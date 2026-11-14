from biblissima.names import (
    build_group_names,
    build_work_names,
    clean_name,
    clean_person_name,
    clean_work_name,
    fetch_person_forms,
    group_of,
)
from biblissima.texts import BiblissimaWork

from conftest import FakeClient


def test_clean_name():
    assert clean_name("Ptolemy (0100?-0170?)") == "Ptolemy"
    assert clean_name("Ptolemy, active 2nd century. Almagest") == "Almagest"
    assert clean_name("Almagest (trad. Gérard)") == "Almagest (trad. Gérard)"  # base keeps it
    assert clean_name("Ptolemaeus, Claudius (0100?-0170?)Ptolemaios (0100?-0170?)") == ""
    assert clean_name("Klaúdios") == "Klaúdios"
    assert clean_name("  ") == "" and clean_name(None) == ""
    assert clean_name("a|b") == ""


def test_clean_person_name():
    assert clean_person_name("Ptolemaeus, Claudius, 100-178") == "Ptolemaeus, Claudius"
    assert clean_person_name("Ptolemaeus, Claudius fl.ca. 100-178") == "Ptolemaeus, Claudius"
    assert clean_person_name("Claudius Ptolemaeus - ca. 100 - ca. 175") == "Claudius Ptolemaeus"
    assert clean_person_name("Ptolemy, 2nd cent.") == "Ptolemy"
    assert clean_person_name("168") == ""
    assert clean_person_name("Ptolemy") == "Ptolemy"


def test_clean_work_name():
    assert clean_work_name("homère, iliade (trad. leonzio pilato)") == "iliade"
    assert clean_work_name("théocrite, poèmes") == "poèmes"
    assert clean_work_name("Almagest (trad. Gérard)") == "Almagest"
    assert clean_work_name("Lysis, or friendship") == "Lysis, or friendship"


def test_group_of():
    assert group_of("urn:cts:greekLit:tlg0363.tlg001:") == "urn:cts:greekLit:tlg0363:"


TEXTS = {"ark:w": ("urn:cts:greekLit:tlg0363.tlg001:", "Claudius Ptolemaeus", "Syntaxis mathematica")}


def _works():
    w = BiblissimaWork(ark="ark:w", title="Almageste")
    w.forms = ["Almageste", "Almagest", "Syntaxis mathematica", "Almagest"]
    return {1: w}


def test_build_work_names():
    assert build_work_names(_works(), TEXTS) == [
        ("urn:cts:greekLit:tlg0363.tlg001:", "Almagest"),
        ("urn:cts:greekLit:tlg0363.tlg001:", "Almageste"),
    ]


def test_build_group_names_needs_wikidata_link():
    forms = {10: ["Ptolemy (0100?-0170?)", "Claudius Ptolemaeus"], 11: ["Other"]}
    args = (_works(), TEXTS, {1: {10, 11}}, {10: "Q1"}, forms)
    rows = build_group_names(*args, {"Q1": ["urn:cts:greekLit:tlg0363:"]})
    assert rows == [("urn:cts:greekLit:tlg0363:", "Ptolemy")]
    assert build_group_names(*args, {}) == []


def test_fetch_person_forms():
    client = FakeClient([[[1, "A"]], [[1, "B"], [2, "C"]]])
    assert fetch_person_forms(client, page_size=10) == {1: ["A", "B"], 2: ["C"]}
