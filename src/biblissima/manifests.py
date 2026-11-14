"""Find manuscripts that have IIIF manifests."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Iterator, Optional

from .client import PortalClient
from .rql import iter_rows

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")

#: Variables: M manuscript, MA its ark, TI its displayed title, U manifest URL.
SELECT = "M,MA,TI,U"
WHERE = (
    "M is Manuscript, M ark MA, M displayed_title TI, "
    "M manifests X, X object_uri E, E uri U"
)
ORDER_BY = "M,U"


@dataclass(frozen=True)
class ManifestRecord:
    """One manuscript / IIIF manifest pair.

    ``collection`` is the institution or collection that holds the manuscript.
    ``qid`` is the manuscript's item in the Biblissima Wikibase (``Q123``), when
    known. ``license`` and ``credits`` are filled in by :mod:`biblissima.rights`.
    """

    biblissima: str
    label: str
    manifest: str
    license: str = ""
    credits: str = ""
    qid: str = ""
    collection: str = ""


def clean_label(raw: Optional[str]) -> str:
    """Remove markup and collapse whitespace in a displayed title."""
    if not raw:
        return ""
    return _SPACE.sub(" ", html.unescape(_TAG.sub("", raw))).strip()


def iter_manifest_records(
    client: PortalClient, *, page_size: int = 2000, limit: Optional[int] = None
) -> Iterator[ManifestRecord]:
    """Yield a :class:`ManifestRecord` for each manuscript/manifest pair.

    A manuscript with several manifests yields several records. Duplicate
    pairs and rows without a manifest URL are skipped. ``limit`` caps the
    number of *records* yielded (useful for trial runs).
    """
    seen: set[tuple[str, str]] = set()
    yielded = 0
    if limit is not None:
        page_size = max(1, min(page_size, limit))
    for row in iter_rows(
        client, SELECT, WHERE, order_by=ORDER_BY, page_size=page_size
    ):
        _eid, ark, title, uri = row
        uri = (uri or "").strip()
        if not ark or not uri:
            continue
        key = (ark, uri)
        if key in seen:
            continue
        seen.add(key)
        yield ManifestRecord(biblissima=ark, label=clean_label(title), manifest=uri)
        yielded += 1
        if limit is not None and yielded >= limit:
            return


QID_SELECT = "MA,QU"
QID_WHERE = (
    "M is Manuscript, M ark MA, M manifests X, M records R, R url QU, "
    'R url LIKE "%data.biblissima.fr/entity/Q%"'
)
_QID = re.compile(r"data\.biblissima\.fr/entity/(Q\d+)")


def iter_qids(
    client: PortalClient, *, page_size: int = 2000, max_rows: Optional[int] = None
) -> Iterator[tuple[str, str]]:
    """Yield ``(ark, qid)`` for manuscripts with a manifest and a Wikibase record.

    The portal links each manuscript to its Wikibase item through a *record*
    whose URL is ``https://data.biblissima.fr/entity/Q...``.
    """
    if max_rows is not None:
        page_size = max(1, min(page_size, max_rows))
    count = 0
    seen: set[str] = set()
    for row in iter_rows(
        client, QID_SELECT, QID_WHERE, order_by="MA,QU", page_size=page_size
    ):
        count += 1
        ark, url = row
        match = _QID.search(url or "")
        if match and ark not in seen:
            seen.add(ark)
            yield ark, match.group(1)
        if max_rows is not None and count >= max_rows:
            return


COLLECTION_SELECT = "MA,CT"
COLLECTION_WHERE = (
    "M is Manuscript, M ark MA, M manifests X, M stored_at C, C displayed_title CT"
)


def iter_collections(
    client: PortalClient, *, page_size: int = 2000
) -> Iterator[tuple[str, str]]:
    """Yield ``(manuscript ark, label of its holding institution)``.

    The portal records the holder as ``Manuscript stored_at CorporateBody``
    (about 99% of manuscripts have one). Only manuscripts with a manifest are
    asked for.
    """
    for ark, title in iter_rows(
        client,
        COLLECTION_SELECT,
        COLLECTION_WHERE,
        order_by="MA,CT",
        page_size=page_size,
        distinct=True,
    ):
        label = clean_label(title)
        if ark and label:
            yield ark, label


def collection_labels(
    client: PortalClient, *, page_size: int = 2000, progress=None
) -> dict[str, str]:
    """``{manuscript ark: label}``; several holders are joined with ``"; "``.

    ``progress``, if given, is called with a message every 20,000 rows.
    """
    found: dict[str, list[str]] = {}
    for n, (ark, label) in enumerate(
        iter_collections(client, page_size=page_size), 1
    ):
        if progress and n % 20000 == 0:
            progress(f"  {n} holder rows read")
        labels = found.setdefault(ark, [])
        if label not in labels:
            labels.append(label)
    return {ark: "; ".join(v) for ark, v in found.items()}
