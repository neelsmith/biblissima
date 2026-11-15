"""Assemble a composite data release file.

A release is one text file made of four blocks. Each block starts with a label
line and runs to the next label line:

``#!version``
    one data line: the contents of the version file (for example ``2026a``)
``#!mss``, ``#!texts``, ``#!textindex``
    the full contents of ``mss.cex``, ``texts.cex`` and ``textindex.cex``,
    header line included

The file is written to ``<out dir>/<version>.cex``.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .client import BiblissimaError

#: Block label and the data file that fills it, in output order.
BLOCKS = (
    ("#!mss", "mss.cex"),
    ("#!texts", "texts.cex"),
    ("#!textindex", "textindex.cex"),
)

_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def read_version(path: Path | str) -> str:
    """Read the version string; it must be one safe word (it names the output file)."""
    version = Path(path).read_text(encoding="utf-8").strip()
    if not _VERSION.match(version):
        raise BiblissimaError(
            f"{path}: version {version!r} must be one word of letters, digits, '.', '_' or '-'"
        )
    return version


def build_release(
    version_file: Path | str,
    data_dir: Path | str,
    out_dir: Path | str,
    *,
    force: bool = False,
) -> Path:
    """Write the release file and return its path.

    :raises BiblissimaError: if an input is missing or empty, or the release
        file already exists and ``force`` is false (published releases should
        not be overwritten by accident).
    """
    version = read_version(version_file)
    data_dir, out_dir = Path(data_dir), Path(out_dir)
    sources = [(label, data_dir / name) for label, name in BLOCKS]
    for _label, src in sources:
        if not src.is_file() or src.stat().st_size == 0:
            raise BiblissimaError(f"missing or empty data file: {src}")
    out = out_dir / f"{version}.cex"
    if out.exists() and not force:
        raise BiblissimaError(f"{out} already exists (use --force to replace it)")
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as dst:
        dst.write(f"#!version\n{version}\n")
        for label, src in sources:
            dst.write(f"{label}\n")
            with src.open(encoding="utf-8", newline="") as fh:
                last = ""
                for chunk in iter(lambda: fh.read(1 << 20), ""):
                    dst.write(chunk)
                    last = chunk
            if not last.endswith("\n"):
                dst.write("\n")
    tmp.replace(out)
    return out


def read_blocks(path: Path | str) -> dict[str, list[str]]:
    """Read a release file into ``{block name: lines}``.

    A block name is the label without its ``#!`` (``version``, ``mss``,
    ``texts``, ``textindex``). Lines are returned without line endings; for the
    data blocks the first line is the header.

    :raises BiblissimaError: if the file has data before the first label.
    """
    blocks: dict[str, list[str]] = {}
    current: list[str] | None = None
    with Path(path).open(encoding="utf-8", newline="") as fh:
        for line in fh:
            line = line.rstrip("\n").rstrip("\r")
            if line.startswith("#!"):
                current = blocks.setdefault(line[2:].strip(), [])
            elif current is None:
                if line.strip():
                    raise BiblissimaError(f"{path}: data before the first #! label")
            else:
                current.append(line)
    return blocks
