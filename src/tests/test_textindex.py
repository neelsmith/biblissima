import tempfile
from pathlib import Path

from biblissima.textindex import (
    HEADER,
    IndexStats,
    build_index,
    iter_text_rows,
    load_column,
    load_work_urns,
    normalize_location,
    shape,
    write_textindex_cex,
)

from conftest import FakeClient


def test_normalize_location():
    assert normalize_location(None) == ""
    assert normalize_location("  ") == ""
    assert normalize_location("176v-177*") == "176v-177"
    assert normalize_location("082-146*") == "82-146"
    assert normalize_location("20r–32v") == "20r-32v"
    assert normalize_location("63bisr") == "63bisr"
    assert normalize_location("170") == "170"
    assert normalize_location("0") == "0"
    assert normalize_location("1--326") == "1-326"
    assert normalize_location("f. 108r-170v") == "108r-170v"
    assert normalize_location("p. 1-89") == "p. 1-89"
    assert normalize_location("32r-v") == "32r-32v"
    assert normalize_location("63bisr-v") == "63bisr-63bisv"
    assert normalize_location("12-21v, 104-133v") == "12-21v, 104-133v"


def test_shape():
    assert shape("20r-32v") == "9a-9a"


def test_build_index_filters_and_dedupes():
    mss = {"m1", "m2"}
    works = {"w1": "urn:cts:greekLit:tlg0001.tlg001:"}
    rows = [
        ("m1", "w1", "20r-32v"),
        ("m1", "w1", "20r-32v"),  # duplicate
        ("m1", "w1", ""),  # same text, no location: dropped
        ("m2", "w1", ""),
        ("m3", "w1", "1"),  # manuscript not in mss.cex
        ("m1", "w9", "1"),  # work not in texts.cex
    ]
    stats = IndexStats()
    out = build_index(rows, mss, works, stats)
    assert out == [
        ("m1", "urn:cts:greekLit:tlg0001.tlg001:", "20r-32v"),
        ("m2", "urn:cts:greekLit:tlg0001.tlg001:", ""),
    ]
    assert (stats.not_in_mss, stats.not_in_texts) == (1, 1)
    assert "9a-9a" in stats.summary()


def test_iter_text_rows_covers_both_depths():
    client = FakeClient([[["m1", 1, "1-2", "w1"]], [["m2", 5, None, "w2"]]])
    rows = list(iter_text_rows(client, page_size=10))
    assert rows == [("m1", "w1", "1-2"), ("m2", "w2", "")]
    assert "has_part C1" in client.queries[1]
    assert "minmax_folios" in client.queries[0]


def test_load_and_write():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "mss.cex").write_text("biblissima|label\nm1|x\nm2|y\n", encoding="utf-8")
        (d / "texts.cex").write_text(
            "biblissima|urn|group|work\nw1|urn:a:|G|W\n", encoding="utf-8"
        )
        assert load_column(d / "mss.cex") == {"m1", "m2"}
        assert load_work_urns(d / "texts.cex") == {"w1": "urn:a:"}
        n = write_textindex_cex([("m1", "urn:a:", "1-2")], d / "t.cex")
        assert n == 1
        assert (d / "t.cex").read_text().splitlines() == ["|".join(HEADER), "m1|urn:a:|1-2"]
