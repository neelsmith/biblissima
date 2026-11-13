"""Cross-index manuscripts and texts (``textindex.cex``).

The portal records which texts a manuscript contains as
``Manuscript has_part Component``, ``Component related_text Text`` and
``Text work Work``. A component sometimes nests inside another component
(never deeper than two levels). A component's ``minmax_folios`` attribute is
a free-text folio range such as ``176v-177*`` or ``082-146*``; it is often
missing.

This module reads those links, keeps only manuscripts listed in ``mss.cex``
and works listed in ``texts.cex``, and writes ``mss|text|location`` rows.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Iterator

from .client import PortalClient
from .export import DELIMITER, write_cex
from .rql import iter_rows

#: Column names of ``textindex.cex``.
HEADER = ("mss", "text", "location")

_SELECT = "MA,C,MM,WA"
_ORDER = "C,WA"
_WHERE = {
    1: "M is Manuscript, M ark MA, M has_part C, C minmax_folios MM, "
    "C related_text T, T work W, W ark WA",
    2: "M is Manuscript, M ark MA, M has_part C1, C1 has_part C, "
    "C minmax_folios MM, C related_text T, T work W, W ark WA",
}

_LEADING_ZEROS = re.compile(r"^0+(?=\d)")


_FOLIO_PREFIX = re.compile(r"^(?:ff?|fol)\.\s*", re.I)
_SIDE_ONLY = re.compile(r"^[rv]$", re.I)
_NUMBER_SIDE = re.compile(r"^(\d+\w*?)([rv])$", re.I)


def normalize_location(raw: str | None) -> str:
    """Tidy a folio range without inventing recto/verso information.

    Whitespace and a trailing ``*`` are removed, en dashes and doubled hyphens
    become ``-``, a ``f.``/``ff.`` prefix is dropped (``p.`` for pages is kept),
    and leading zeros are dropped from each end of a range (``082-146`` becomes
    ``82-146``). A range ending in a bare side, ``32r-v``, is written out as
    ``32r-32v``. Folio labels stay strings: ``63bisr`` is left alone. A bare
    number stays bare, because the source does not say which side is meant.
    Lists (``12-21v, 104-133v``) and other free text are only tidied.
    """
    if raw is None:
        return ""
    text = str(raw).strip().rstrip("*").strip().replace("\u2013", "-")
    text = _FOLIO_PREFIX.sub("", re.sub(r"-{2,}", "-", text))
    parts = [_LEADING_ZEROS.sub("", p.strip()) for p in text.split("-")]
    if len(parts) == 2 and _SIDE_ONLY.match(parts[1]):
        m = _NUMBER_SIDE.match(parts[0])
        if m:
            parts[1] = m.group(1) + parts[1].lower()
    return "-".join(parts) if any(parts) else ""


def shape(value: str) -> str:
    """Return a coarse pattern of ``value`` (digits to ``9``, letters to ``a``)."""
    return re.sub(r"[A-Za-z]+", "a", re.sub(r"\d+", "9", value))


def load_column(path: Path | str, column: int = 0) -> set[str]:
    """Return the values of one column of a pipe-delimited file (header skipped)."""
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=DELIMITER)
        next(reader)
        return {row[column] for row in reader if row}


def load_work_urns(path: Path | str) -> dict[str, str]:
    """Map Biblissima work identifiers to CTS URNs, from ``texts.cex``."""
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=DELIMITER)
        return {r["biblissima"]: r["urn"] for r in reader}


def iter_text_rows(
    client: PortalClient, *, page_size: int = 5000, limit: int | None = None
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(manuscript ark, work ark, raw folio range)`` for every text link."""
    for depth in (1, 2):
        for ma, _c, mm, wa in iter_rows(
            client,
            _SELECT,
            _WHERE[depth],
            order_by=_ORDER,
            page_size=page_size,
            limit=limit,
        ):
            yield ma, wa, mm or ""


class IndexStats:
    """Counts gathered while building the index."""

    def __init__(self) -> None:
        self.rows_seen = 0
        self.kept = 0
        self.with_location = 0
        self.not_in_mss = 0
        self.not_in_texts = 0
        self.shapes: Counter[str] = Counter()
        self.examples: dict[str, str] = {}

    def summary(self) -> str:
        lines = [
            f"{self.rows_seen} manuscript-text links read; "
            f"{self.kept} kept ({self.with_location} with a location)",
            f"skipped: {self.not_in_mss} manuscripts not in mss.cex, "
            f"{self.not_in_texts} works not in texts.cex",
            "location patterns (9 = digits, a = letters):",
        ]
        for pat, n in self.shapes.most_common(25):
            lines.append(f"  {n:7d}  {pat!r:24}  e.g. {self.examples[pat]!r}")
        return "\n".join(lines)


def build_index(
    rows: Iterable[tuple[str, str, str]],
    mss: set[str],
    works: dict[str, str],
    stats: IndexStats | None = None,
) -> list[tuple[str, str, str]]:
    """Filter and normalise link rows; return sorted unique ``(mss, urn, location)``."""
    stats = stats or IndexStats()
    out: set[tuple[str, str, str]] = set()
    for ma, wa, mm in rows:
        stats.rows_seen += 1
        if ma not in mss:
            stats.not_in_mss += 1
            continue
        if wa not in works:
            stats.not_in_texts += 1
            continue
        loc = normalize_location(mm)
        if loc:
            stats.with_location += 1
            pat = shape(loc)
            stats.shapes[pat] += 1
            stats.examples.setdefault(pat, loc)
        out.add((ma, works[wa], loc))
        stats.kept += 1
    # A text found once with a location and once without keeps only the former.
    located = {(m, u) for m, u, loc in out if loc}
    return sorted(r for r in out if r[2] or (r[0], r[1]) not in located)


def write_textindex_cex(rows: Iterable[tuple[str, str, str]], path: Path | str) -> int:
    """Write ``textindex.cex``; return the row count."""
    return write_cex(path, HEADER, rows)
