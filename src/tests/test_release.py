import tempfile
from pathlib import Path

from biblissima import BiblissimaError
from biblissima.release import build_release, read_version
from biblissima.cli import main

import pytest


def _setup(d, version="2026a\n"):
    d = Path(d)
    (d / "data").mkdir()
    (d / "v.txt").write_text(version)
    (d / "data" / "mss.cex").write_text("biblissima|label\nm1|x\n")
    (d / "data" / "texts.cex").write_text("biblissima|urn\nw1|u")  # no final newline
    (d / "data" / "textindex.cex").write_text("mss|text|location\nm1|u|1-2\n")
    return d


def test_build_release():
    with tempfile.TemporaryDirectory() as t:
        d = _setup(t)
        out = build_release(d / "v.txt", d / "data", d / "rel")
        assert out == d / "rel" / "2026a.cex"
        assert out.read_text().splitlines() == [
            "#!version", "2026a",
            "#!mss", "biblissima|label", "m1|x",
            "#!texts", "biblissima|urn", "w1|u",
            "#!textindex", "mss|text|location", "m1|u|1-2",
        ]
        assert not (d / "rel" / "2026a.cex.part").exists()


def test_refuses_overwrite_unless_forced():
    with tempfile.TemporaryDirectory() as t:
        d = _setup(t)
        build_release(d / "v.txt", d / "data", d / "rel")
        with pytest.raises(BiblissimaError):
            build_release(d / "v.txt", d / "data", d / "rel")
        build_release(d / "v.txt", d / "data", d / "rel", force=True)


def test_bad_inputs():
    with tempfile.TemporaryDirectory() as t:
        d = _setup(t)
        (d / "data" / "texts.cex").write_text("")
        with pytest.raises(BiblissimaError):
            build_release(d / "v.txt", d / "data", d / "rel")
        (d / "v.txt").write_text("../evil")
        with pytest.raises(BiblissimaError):
            read_version(d / "v.txt")
        (d / "v.txt").write_text("")
        with pytest.raises(BiblissimaError):
            read_version(d / "v.txt")


def test_cli_release():
    with tempfile.TemporaryDirectory() as t:
        d = _setup(t)
        rc = main(["release", "--version-file", str(d / "v.txt"),
                   "--data-dir", str(d / "data"), "--out-dir", str(d / "rel")])
        assert rc == 0 and (d / "rel" / "2026a.cex").is_file()
        assert main(["release", "--version-file", str(d / "v.txt"),
                     "--data-dir", str(d / "data"), "--out-dir", str(d / "rel")]) == 1
