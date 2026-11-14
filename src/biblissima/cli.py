"""Command-line interface: ``biblissima mss``."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import __version__
from .client import (
    DEFAULT_BASE_URL,
    DEFAULT_USER_AGENT,
    DEFAULT_WIKIBASE_URL,
    BiblissimaError,
    PortalClient,
    Throttle,
    WikibaseClient,
)
from .export import write_mss_cex
from .harvest import build_mss_records
from .rights import RightsStats
from .names import (
    build_group_names,
    build_work_names,
    fetch_person_forms,
    fetch_person_qids,
    fetch_work_authors,
    load_texts,
    write_names_cex,
)
from .textindex import (
    IndexStats,
    build_index,
    iter_text_rows,
    load_column,
    load_work_urns,
    write_textindex_cex,
)
from .texts import (
    attach_authors,
    fetch_works,
    match_work,
    split_matches,
    write_review_cex,
    write_texts_cex,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biblissima", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    mss = sub.add_parser(
        "mss", help="write data/mss.cex: one row per manuscript IIIF manifest"
    )
    mss.add_argument("--out", default="data/mss.cex", help="output file")
    mss.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="sent to the server; add a contact address when harvesting",
    )
    mss.add_argument("--base-url", default=DEFAULT_BASE_URL)
    mss.add_argument("--wikibase-url", default=DEFAULT_WIKIBASE_URL)
    mss.add_argument(
        "--no-rights",
        action="store_true",
        help="skip the Wikibase lookups; license and credits stay empty",
    )
    mss.add_argument("--page-size", type=int, default=2000)
    mss.add_argument("--limit", type=int, default=None, help="stop after N records")
    mss.add_argument(
        "--min-interval",
        type=float,
        default=1.0,
        help="minimum seconds between requests (default 1.0)",
    )
    mss.add_argument(
        "--cache-dir", default=None, help="cache raw responses here to allow resuming"
    )

    texts = sub.add_parser(
        "texts", help="write data/texts.cex: Biblissima works matched to CTS work URNs"
    )
    texts.add_argument("--out", default="data/texts.cex")
    texts.add_argument("--review", default="data/texts_review.cex")
    texts.add_argument(
        "--cts", nargs="+", required=True, help="directories holding __cts__.xml files"
    )
    texts.add_argument(
        "--wikidata",
        required=True,
        help="saved SPARQL JSON mapping Wikidata items to TLG/PHI author ids",
    )
    texts.add_argument("--threshold", type=float, default=0.85)
    texts.add_argument("--review-threshold", type=float, default=0.6)
    texts.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    texts.add_argument("--base-url", default=DEFAULT_BASE_URL)
    texts.add_argument("--page-size", type=int, default=2000)
    texts.add_argument("--min-interval", type=float, default=1.0)
    texts.add_argument("--cache-dir", default=None)

    nm = sub.add_parser(
        "names",
        help="write data/groupnames.cex and data/worknames.cex: alternative names",
    )
    nm.add_argument("--texts", default="data/texts.cex")
    nm.add_argument("--wikidata", default="data/wikidata_tlg_phi.json")
    nm.add_argument("--out-groups", default="data/groupnames.cex")
    nm.add_argument("--out-works", default="data/worknames.cex")
    nm.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    nm.add_argument("--base-url", default=DEFAULT_BASE_URL)
    nm.add_argument("--page-size", type=int, default=2000)
    nm.add_argument("--min-interval", type=float, default=1.0)
    nm.add_argument("--cache-dir", default=None)

    ti = sub.add_parser(
        "textindex", help="write data/textindex.cex: which texts are in which manuscripts"
    )
    ti.add_argument("--out", default="data/textindex.cex")
    ti.add_argument("--mss", default="data/mss.cex")
    ti.add_argument("--texts", default="data/texts.cex")
    ti.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    ti.add_argument("--base-url", default=DEFAULT_BASE_URL)
    ti.add_argument("--page-size", type=int, default=5000)
    ti.add_argument("--limit", type=int, default=None, help="rows per query (testing)")
    ti.add_argument("--min-interval", type=float, default=1.0)
    ti.add_argument("--cache-dir", default=None)
    return parser


def _run_texts(args: argparse.Namespace) -> int:
    from .cts import load_catalog
    from .wikidata import load_group_urns

    catalog = load_catalog(args.cts)
    print(
        f"CTS catalogue: {len(catalog.groups)} groups, {len(catalog.works)} works",
        file=sys.stderr,
    )
    group_urns = load_group_urns(args.wikidata)
    portal = PortalClient(
        base_url=args.base_url,
        user_agent=args.user_agent,
        min_interval=args.min_interval,
        cache_dir=args.cache_dir,
    )
    portal.check_endpoint()
    works = fetch_works(portal, page_size=args.page_size)
    print(f"{len(works)} Biblissima works", file=sys.stderr)
    attach_authors(portal, works, page_size=args.page_size)
    with_group = [
        w
        for w in works.values()
        if any(
            g in catalog.groups for q in w.author_qids for g in group_urns.get(q, [])
        )
    ]
    print(f"{len(with_group)} works have an author in a CTS text group", file=sys.stderr)
    if not with_group:
        raise BiblissimaError(
            "no Biblissima work has an author in a CTS text group: check that the "
            "Wikidata file maps authors to TLG/PHI numbers that exist in the CTS catalogue"
        )
    accepted, review = split_matches(
        (match_work(w, catalog, group_urns) for w in with_group),
        args.threshold,
        args.review_threshold,
    )
    n = write_texts_cex(accepted, args.out)
    r = write_review_cex(review, args.review)
    print(f"wrote {n} rows to {args.out}; {r} to review in {args.review}", file=sys.stderr)
    return 0


def _run_names(args: argparse.Namespace) -> int:
    from .wikidata import load_group_urns

    texts = load_texts(args.texts)
    group_urns = load_group_urns(args.wikidata)
    portal = PortalClient(
        base_url=args.base_url,
        user_agent=args.user_agent,
        min_interval=args.min_interval,
        cache_dir=args.cache_dir,
    )
    portal.check_endpoint()
    works = fetch_works(portal, page_size=args.page_size)
    work_authors = fetch_work_authors(portal, args.page_size)
    person_qids = fetch_person_qids(portal, args.page_size)
    person_forms = fetch_person_forms(portal)
    print(
        f"{len(texts)} texts; {len(person_forms)} persons with name forms",
        file=sys.stderr,
    )
    work_rows = build_work_names(works, texts)
    group_rows = build_group_names(
        works, texts, work_authors, person_qids, person_forms, group_urns
    )
    w = write_names_cex(work_rows, args.out_works)
    g = write_names_cex(group_rows, args.out_groups)
    print(f"wrote {g} group names to {args.out_groups}", file=sys.stderr)
    print(f"wrote {w} work names to {args.out_works}", file=sys.stderr)
    return 0


def _run_textindex(args: argparse.Namespace) -> int:
    mss = load_column(args.mss)
    works = load_work_urns(args.texts)
    print(f"{len(mss)} manuscripts, {len(works)} texts", file=sys.stderr)
    portal = PortalClient(
        base_url=args.base_url,
        user_agent=args.user_agent,
        min_interval=args.min_interval,
        cache_dir=args.cache_dir,
    )
    portal.check_endpoint()
    stats = IndexStats()

    def progress():
        for i, row in enumerate(
            iter_text_rows(portal, page_size=args.page_size, limit=args.limit), 1
        ):
            if i % 20000 == 0:
                print(f"  {i} links read", file=sys.stderr)
            yield row

    rows = build_index(progress(), mss, works, stats)
    n = write_textindex_cex(rows, args.out)
    print(stats.summary(), file=sys.stderr)
    print(f"wrote {n} rows to {args.out}", file=sys.stderr)
    return 0


def _run_mss(args: argparse.Namespace) -> int:
    throttle = Throttle(args.min_interval)  # shared: portal + Wikibase combined
    common = dict(
        user_agent=args.user_agent, throttle=throttle, cache_dir=args.cache_dir
    )
    portal = PortalClient(base_url=args.base_url, **common)
    wikibase = (
        None
        if args.no_rights
        else WikibaseClient(base_url=args.wikibase_url, **common)
    )
    total = portal.check_endpoint()
    print(f"portal reports {total} manuscripts", file=sys.stderr)

    stats = RightsStats()

    def records():
        for i, rec in enumerate(
            build_mss_records(
                portal,
                wikibase,
                page_size=args.page_size,
                limit=args.limit,
                stats=stats,
            ),
            1,
        ):
            if i % 100 == 0:
                print(f"  {i} records", file=sys.stderr)
            yield rec

    n = write_mss_cex(records(), args.out)
    print(f"wrote {n} records to {args.out}", file=sys.stderr)
    if wikibase is not None:
        print(stats.summary(), file=sys.stderr)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "mss":
            return _run_mss(args)
        if args.command == "texts":
            return _run_texts(args)
        if args.command == "names":
            return _run_names(args)
        if args.command == "textindex":
            return _run_textindex(args)
    except BiblissimaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
