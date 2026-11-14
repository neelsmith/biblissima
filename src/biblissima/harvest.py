"""Assemble the records written to ``mss.cex``."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable, Iterator, Optional

from .client import PortalClient, WikibaseClient
from .manifests import (
    ManifestRecord,
    collection_labels,
    iter_manifest_records,
    iter_qids,
)
from .rights import RightsResolver, RightsStats


def build_mss_records(
    portal: PortalClient,
    wikibase: Optional[WikibaseClient] = None,
    *,
    page_size: int = 2000,
    limit: Optional[int] = None,
    batch: int = 50,
    collections: bool = True,
    progress: Optional[Callable[[str], None]] = None,
    stats: Optional[RightsStats] = None,
) -> Iterator[ManifestRecord]:
    """Yield one record per manuscript IIIF manifest, with rights if possible.

    Without ``wikibase`` the ``license`` and ``credits`` fields stay empty.
    With it, the portal first supplies each manuscript's Wikibase item, then
    items are fetched ``batch`` at a time and the digital library behind each
    manifest is looked up (see :mod:`biblissima.rights`).

    :param limit: stop after this many records (trial runs).
    """
    stats = stats if stats is not None else RightsStats()
    records = iter_manifest_records(portal, page_size=page_size, limit=limit)
    if wikibase is None:
        holders = _holders(portal, collections, page_size, progress)
        for rec in records:
            stats.records += 1
            yield replace(rec, collection=holders.get(rec.biblissima, ""))
        return

    max_rows = None if limit is None else 2 * limit + 50
    if progress:
        progress("reading Wikibase item ids ...")
    qids = dict(iter_qids(portal, page_size=page_size, max_rows=max_rows))
    if progress:
        progress(f"  {len(qids)} manuscripts have a Wikibase item")
    holders = _holders(portal, collections, page_size, progress)
    if progress:
        progress("reading manifests ...")
    resolver = RightsResolver(wikibase)
    buffer: list[ManifestRecord] = []

    def flush() -> Iterator[ManifestRecord]:
        resolver.prefetch(r.qid for r in buffer)
        for rec in buffer:
            stats.records += 1
            if not rec.qid:
                stats.no_qid += 1
                yield rec
                continue
            licence, credits = resolver.rights_for(rec.qid, rec.manifest)
            if not credits:
                stats.no_library += 1
            if licence:
                stats.with_license += 1
            yield replace(rec, license=licence, credits=credits)
        buffer.clear()

    for rec in records:
        buffer.append(
            replace(
                rec,
                qid=qids.get(rec.biblissima, ""),
                collection=holders.get(rec.biblissima, ""),
            )
        )
        if len({r.qid for r in buffer if r.qid}) >= batch:
            yield from flush()
    yield from flush()


def _holders(
    portal: PortalClient, wanted: bool, page_size: int, progress=None
) -> dict[str, str]:
    if not wanted:
        return {}
    if progress:
        progress("reading holding institutions ...")
    found = collection_labels(portal, page_size=page_size, progress=progress)
    if progress:
        progress(f"  {len(found)} manuscripts have a holding institution")
    return found
