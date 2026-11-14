from biblissima.harvest import build_mss_records
from biblissima.manifests import collection_labels, iter_qids
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
            collections=False,
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
    recs = list(build_mss_records(FakeClient([main_rows]), None, page_size=10, collections=False))
    assert recs[0].license == "" and recs[0].credits == ""


def test_collection_labels_join_and_clean():
    rows = [
        ["ark:/1", "Vatican. <i>Biblioteca</i> apostolica vaticana"],
        ["ark:/2", "BnF"],
        ["ark:/2", "Sainte-Geneviève"],
        ["ark:/2", "BnF"],
        ["ark:/3", ""],
    ]
    assert collection_labels(FakeClient([rows]), page_size=10) == {
        "ark:/1": "Vatican. Biblioteca apostolica vaticana",
        "ark:/2": "BnF; Sainte-Geneviève",
    }


def test_progress_messages():
    msgs = []
    holders = [["ark:/1", "Vatican"]]
    main_rows = [[1, "ark:/1", "One", "http://vat/m.json"]]
    list(build_mss_records(FakeClient([holders, main_rows]), None, page_size=10, progress=msgs.append))
    assert any("holding institutions" in m for m in msgs)


def test_records_get_collection():
    holders = [["ark:/1", "Vatican. Biblioteca apostolica vaticana"]]
    main_rows = [[1, "ark:/1", "One", "http://vat/m.json"], [2, "ark:/2", "Two", "http://z/m"]]
    recs = list(build_mss_records(FakeClient([holders, main_rows]), None, page_size=10))
    assert [r.collection for r in recs] == ["Vatican. Biblioteca apostolica vaticana", ""]


def test_records_get_collection_with_rights():
    qid_rows = [["ark:/1", "https://data.biblissima.fr/entity/Q1"]]
    holders = [["ark:/1", "Vatican"]]
    main_rows = [[1, "ark:/1", "One", "http://vat/m.json"]]
    recs = list(
        build_mss_records(
            FakeClient([qid_rows, holders, main_rows]), FakeWikibase(entities()), page_size=10
        )
    )
    assert recs[0].collection == "Vatican" and recs[0].credits
