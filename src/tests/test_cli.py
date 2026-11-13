import tempfile
from pathlib import Path

from biblissima import cli

from conftest import FakeClient, load_json


def test_mss_command_writes_file():
    rows = load_json("pal_gr_348_rows.json")
    fake = FakeClient([rows])
    fake.check_endpoint = lambda: 338731
    original = cli.PortalClient
    cli.PortalClient = lambda **kw: fake
    try:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "mss.cex"
            code = cli.main(["mss", "--out", str(out), "--limit", "5", "--no-rights"])
            text = out.read_text(encoding="utf-8")
    finally:
        cli.PortalClient = original
    assert code == 0
    assert text.splitlines()[0].startswith("biblissima|label|manifest")
    assert "Pal.gr.348" in text


def test_parser_defaults():
    args = cli.build_parser().parse_args(["mss"])
    assert args.out == "data/mss.cex"
    assert args.min_interval == 1.0


def test_parser_rights_flags():
    args = cli.build_parser().parse_args(["mss", "--no-rights"])
    assert args.no_rights is True
    assert cli.build_parser().parse_args(["mss"]).no_rights is False
