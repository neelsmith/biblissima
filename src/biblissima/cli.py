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
    return parser


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
    except BiblissimaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
