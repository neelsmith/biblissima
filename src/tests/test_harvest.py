from biblissima.harvest import build_mss_records
from biblissima.manifests import iter_qids
from biblissima.rights import RightsStats

from conftest import FakeClient, FakeWikibase
from test_rights import entities


def test_iter_qids_extracts_ids_and_dedupes():
    rows = [
        ["ark:/1", "https://data.biblissima.fr/entity/Q1"],
        ["ark:/1", "https://data.biblissima.fr/entity/Q1"],
        ["ark:/2", "https://data.biblissima.fr/entity/Q22"],
        ["ark:/3", "https://example.org/other"],
    ]
    assert list(iter_qids(FakeClient([rows]), page_size=10)) == [
        ("ark:/1", "Q1"),
        ("ark:/2", "Q22"),
    ]


def test_records_get_rights_from_wikibase():
    # FakeClient serves pages in call order: the QID pass first, then the main pass.
    qid_rows = [
        ["ark:/1", "https://data.biblissima.fr/entity/Q1"],
        ["ark:/2", "https://data.biblissima.fr/entity/Q2"],
    ]
    main_rows = [
        [1, "ark:/1", "One", "http://vat/m.json"],
        [2, "ark:/2", "Two", "http://arca/m.json"],
        [2, "ark:/2", "Two", "http://other/m.json"],
        [3, "ark:/3", "Three (no item)", "http://z/m.json"],
    ]
    stats = RightsStats()
    recs = list(
        build_mss_records(
            FakeClient([qid_rows, main_rows]),
            FakeWikibase(entities()),
            page_size=10,
            stats=stats,
        )
    )
    by_ark = {(r.biblissima, r.manifest): r for r in recs}
    assert by_ark[("ark:/1", "http://vat/m.json")].credits.startswith("DigitVatLib")
    assert by_ark[("ark:/2", "http://arca/m.json")].license.startswith("CC BY-NC")
    assert by_ark[("ark:/2", "http://other/m.json")].credits == ""
    assert by_ark[("ark:/3", "http://z/m.json")].qid == ""
    assert (stats.records, stats.no_qid, stats.no_library, stats.with_license) == (4, 1, 1, 1)


def test_without_wikibase_records_have_no_rights():
    main_rows = [[1, "ark:/1", "One", "http://vat/m.json"]]
    recs = list(build_mss_records(FakeClient([main_rows]), None, page_size=10))
    assert recs[0].license == "" and recs[0].credits == ""
