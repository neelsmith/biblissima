import tempfile
from pathlib import Path

from biblissima import HEADER, ManifestRecord, write_mss_cex
from biblissima.export import sanitize


def test_header_constant():
    assert "|".join(HEADER) == "biblissima|label|manifest|manifest_license|manifest_credits"


def test_sanitize():
    assert sanitize("a\n b\t c ") == "a b c"
    assert sanitize(None) == ""


def test_write_file_content():
    recs = [
        ManifestRecord("ark:/1", "Label one", "http://m/1", "CC0", "BnF"),
        ManifestRecord("ark:/2", "Has | pipe\nand newline", "http://m/2"),
    ]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "data" / "mss.cex"
        n = write_mss_cex(recs, out)
        lines = out.read_text(encoding="utf-8").split("\n")
        assert not Path(str(out) + ".part").exists()
    assert n == 2
    assert lines[0] == "biblissima|label|manifest|manifest_license|manifest_credits"
    assert lines[1] == "ark:/1|Label one|http://m/1|CC0|BnF"
    assert lines[2] == 'ark:/2|"Has | pipe and newline"|http://m/2||'
    assert lines[3] == ""


def test_round_trip_with_csv_reader():
    import csv

    recs = [ManifestRecord("ark:/2", 'Say "hi" | now', "http://m/2")]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "mss.cex"
        write_mss_cex(recs, out)
        with out.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh, delimiter="|"))
    assert rows[1][1] == 'Say "hi" | now'
    assert len(rows[1]) == 5
