from biblissima.manifests import ManifestRecord, clean_label, iter_manifest_records

from conftest import FakeClient, load_json


def test_clean_label_strips_markup_and_whitespace():
    assert clean_label("<i>Pal.gr.</i>  348 &amp; co\n") == "Pal.gr. 348 & co"
    assert clean_label(None) == ""


def test_records_from_fixture_row():
    client = FakeClient([load_json("pal_gr_348_rows.json")])
    recs = list(iter_manifest_records(client, page_size=10))
    assert recs == [
        ManifestRecord(
            biblissima="ark:/43093/mdata60119c636ac27834e52a0179c8baafd3a34857ed",
            label="Vatican. Biblioteca apostolica vaticana, Pal.gr.348",
            manifest="https://digi.vatlib.it/iiif/MSS_Pal.gr.348/manifest.json",
        )
    ]


def test_duplicates_and_missing_urls_are_skipped():
    rows = [
        [1, "ark:/1", "A", "http://m/1"],
        [1, "ark:/1", "A", "http://m/1"],
        [1, "ark:/1", "A", "http://m/2"],
        [2, "ark:/2", "B", ""],
        [3, "ark:/3", "C", None],
    ]
    recs = list(iter_manifest_records(FakeClient([rows]), page_size=10))
    assert [(r.biblissima, r.manifest) for r in recs] == [
        ("ark:/1", "http://m/1"),
        ("ark:/1", "http://m/2"),
    ]


def test_limit_caps_records_and_page_size():
    rows = [[i, f"ark:/{i}", f"L{i}", f"http://m/{i}"] for i in range(5)]
    client = FakeClient([rows[:2]])
    recs = list(iter_manifest_records(client, page_size=1000, limit=2))
    assert len(recs) == 2
    assert "LIMIT 2 " in client.queries[0]
