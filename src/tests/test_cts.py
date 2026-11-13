from pathlib import Path

import pytest

from biblissima.cts import group_urn, load_catalog, pick_name, work_urn
from biblissima.wikidata import load_group_urns

DATA = Path(__file__).parent / "data"


def test_urns_get_trailing_colon():
    assert work_urn("urn:cts:greekLit:tlg0363.tlg001") == "urn:cts:greekLit:tlg0363.tlg001:"
    assert work_urn("urn:cts:greekLit:tlg0363.tlg001:") == "urn:cts:greekLit:tlg0363.tlg001:"
    assert group_urn("urn:cts:greekLit:tlg0363") == "urn:cts:greekLit:tlg0363:"
    assert group_urn("urn:cts:greekLit:tlg0363.tlg001") == "urn:cts:greekLit:tlg0363:"


def test_urn_validation():
    for bad in ["urn:cts:greekLit", "tlg0363", "urn:cts:greekLit:tlg0363"]:
        with pytest.raises(ValueError):
            work_urn(bad)
    with pytest.raises(ValueError):
        group_urn("nonsense")


def test_five_components_four_colons():
    assert work_urn("urn:cts:latinLit:phi0690.phi003").count(":") == 4
    assert group_urn("urn:cts:latinLit:phi0690").count(":") == 4


def test_pick_name_prefers_english_then_latin():
    assert pick_name({"lat": "Syntaxis", "eng": "Almagest"}) == "Almagest"
    assert pick_name({"grc": "x", "lat": "y"}) == "y"
    assert pick_name({"fre": "z"}) == "z"
    assert pick_name({}) == ""


def test_load_catalog_from_fixture_files():
    cat = load_catalog([DATA / "cts" / "First1KGreek", DATA / "cts" / "canonical-greekLit"])
    ptol = cat.groups["urn:cts:greekLit:tlg0363:"]
    assert ptol.name == "Claudius Ptolemaeus"
    work = cat.works["urn:cts:greekLit:tlg0363.tlg001:"]
    assert work.title == "Syntaxis mathematica"
    assert work.group_urn == "urn:cts:greekLit:tlg0363:"
    assert {w.urn for w in cat.works_in_group("urn:cts:greekLit:tlg0363:")} == {
        "urn:cts:greekLit:tlg0363.tlg001:",
        "urn:cts:greekLit:tlg0363.tlg007:",
    }
    assert cat.works_in_group("urn:cts:greekLit:nope:") == []


def test_wikidata_mapping_pads_numbers():
    m = load_group_urns(DATA / "wikidata_tlg_phi.json")
    assert m["Q34943"] == ["urn:cts:greekLit:tlg0363:"]
    assert m["Q1398"] == ["urn:cts:latinLit:phi0690:"]


def test_wikidata_rejects_wrong_properties():
    import json
    import tempfile

    bad = {"results": {"bindings": [
        {"p": {"value": "http://www.wikidata.org/entity/Q1"}, "tlg": {"value": "http://www.wikidata.org/entity/Q136257"}}
        for _ in range(20)
    ]}}
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "x.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError):
            load_group_urns(path)
