"""Write harvested records to delimited text files."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable, Sequence

from .manifests import ManifestRecord

#: Column names of ``mss.cex``.
HEADER = ("biblissima", "label", "manifest", "manifest_license", "manifest_credits")
DELIMITER = "|"

_WHITESPACE = re.compile(r"\s+")


def sanitize(value: str) -> str:
    """Make a value safe for a one-line-per-record file.

    Line breaks and tabs become spaces and runs of whitespace are collapsed.
    The delimiter itself is left alone: the writer quotes fields that
    contain it.
    """
    return _WHITESPACE.sub(" ", value or "").strip()


def write_cex(
    path: Path | str, header: Sequence[str], rows: Iterable[Sequence[str]]
) -> int:
    """Write rows to ``path`` as a pipe-delimited file; return the row count.

    The file is written to a temporary name and renamed on success, so an
    interrupted run never leaves a half-written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    count = 0
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(
            fh, delimiter=DELIMITER, quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
        )
        writer.writerow(header)
        for row in rows:
            writer.writerow([sanitize(str(v)) for v in row])
            count += 1
    tmp.replace(path)
    return count


def write_mss_cex(records: Iterable[ManifestRecord], path: Path | str) -> int:
    """Write manuscript manifest records to ``mss.cex``; return the row count."""
    return write_cex(
        path,
        HEADER,
        (
            (r.biblissima, r.label, r.manifest, r.license, r.credits)
            for r in records
        ),
    )
