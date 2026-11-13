"""Write harvested records to delimited text files."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

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


def write_mss_cex(records: Iterable[ManifestRecord], path: Path | str) -> int:
    """Write ``records`` to ``path`` as a pipe-delimited file; return the row count.

    The file is written to a temporary name and renamed on success, so an
    interrupted run never leaves a half-written ``mss.cex``.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    count = 0
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(
            fh, delimiter=DELIMITER, quoting=csv.QUOTE_MINIMAL, lineterminator="\n"
        )
        writer.writerow(HEADER)
        for rec in records:
            writer.writerow(
                [
                    sanitize(rec.biblissima),
                    sanitize(rec.label),
                    sanitize(rec.manifest),
                    sanitize(rec.license),
                    sanitize(rec.credits),
                ]
            )
            count += 1
    tmp.replace(path)
    return count
