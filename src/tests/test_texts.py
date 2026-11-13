import tempfile
from pathlib import Path

from biblissima.cts import load_catalog
from biblissima.texts import (
    BiblissimaWork,
    TextMatch,
    attach_authors,
    fetch_works,
    fold,
    match_work,
    split_matches,
    strip_author,
    title_score,
    write_review_cex,
    write_texts_cex,
)
from biblissima.wikidata import load_group_urns

from conftest import FakeClient

DATA = Path(__file__).parent / "data"
CAT = load_catalog([DATA / "cts" / "First1KGreek", DATA / "cts" / "canonical-greekLit"])
WD = load_group_urns(DATA / "wikidata_tlg_phi.json")


def test_fold_and_strip_author():
    assert fold("L'Odyssée !") == "odyssee"
    assert fold("De la Syntaxis Mathématique") == "syntaxis mathematique"
    assert strip_author("Homère : Odyssée") == "Odyssée"
    assert strip_author("Almageste") == "Almageste"
    assert strip_author("X : ") == "X :"


def test_title_score():
    assert title_score(["Odyssée"], ["Odyssea"]) > 0.8
    assert title_score(["Tetrabiblos"], ["Tetrabiblos"]) == 1.0
    assert title_score(["Harmoniques"], ["Syntaxis mathematica"]) < 0.5
    assert title_score([], ["x"]) == 0.0


def test_match_requires_author_group():
    w = BiblissimaWork("ark:/1", "Claude Ptolémée : Tetrabiblos", author_qids={"Q999"})
    assert match_work(w, CAT, WD) == []


def test_exact_title_match_within_group():
    w = BiblissimaWork("ark:/1", "Claude Ptolémée (0100?-0170?) : Tetrabiblos", author_qids={"Q34943"})
    (m,) = match_work(w, CAT, WD)
    assert m.urn == "urn:cts:greekLit:tlg0363.tlg007:"
    assert m.group == "Claudius Ptolemaeus"
    assert m.work == "Tetrabiblos"
    assert m.score == 1.0


def test_other_forms_can_supply_the_match():
    w = BiblissimaWork("ark:/2", "Almageste", forms=["Syntaxis mathematica"], author_qids={"Q34943"})
    (m,) = match_work(w, CAT, WD)
    assert m.urn == "urn:cts:greekLit:tlg0363.tlg001:"


def test_split_matches_threshold_and_ambiguity():
    strong = TextMatch("a", "l", "urn:cts:greekLit:g.w1:", "G", "W1", 0.95)
    weak = TextMatch("b", "l", "urn:cts:greekLit:g.w2:", "G", "W2", 0.7)
    tie1 = TextMatch("c", "l", "urn:cts:greekLit:g.w3:", "G", "W3", 0.95)
    tie2 = TextMatch("c", "l", "urn:cts:greekLit:g.w4:", "G", "W4", 0.95)
    low = TextMatch("d", "l", "urn:cts:greekLit:g.w5:", "G", "W5", 0.3)
    accepted, review = split_matches([[strong], [weak], [tie1, tie2], [low], []], 0.85, 0.6)
    assert accepted == [strong]
    assert review == [weak, tie1, tie2]


def test_write_texts_cex_format():
    m = [
        TextMatch("ark:/2", "l", "urn:cts:greekLit:tlg0363.tlg001:", "Claudius Ptolemaeus", "Syntaxis mathematica", 1.0),
        TextMatch("ark:/2", "l", "urn:cts:greekLit:tlg0363.tlg001:", "Claudius Ptolemaeus", "Syntaxis mathematica", 1.0),
    ]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "texts.cex"
        assert write_texts_cex(m, out) == 1
        lines = out.read_text(encoding="utf-8").splitlines()
        review = Path(d) / "r.cex"
        write_review_cex(m, review)
        rlines = review.read_text(encoding="utf-8").splitlines()
    assert lines == [
        "biblissima|urn|group|work",
        "ark:/2|urn:cts:greekLit:tlg0363.tlg001:|Claudius Ptolemaeus|Syntaxis mathematica",
    ]
    assert rlines[0] == "biblissima|urn|group|work|score|label"
    assert rlines[1].endswith("|1.000|l")


def test_fetch_works_and_authors_from_portal_pages():
    pages = [
        [[10, "ark:/10", "Claude Ptolémée : Tetrabiblos"], [11, "ark:/11", "Almageste"]],  # works
        [[11, "Almageste"]],  # preferred_form
        [[11, "Syntaxis mathematica"]],  # other_forms
        [[100, "http://www.wikidata.org/entity/Q34943"], [101, "http://example.org/x"]],  # persons
        [[10, 100], [11, 100], [11, 101]],  # authors
    ]
    client = FakeClient(pages)
    works = fetch_works(client, page_size=50)
    assert works[11].forms == ["Almageste", "Syntaxis mathematica"]
    attach_authors(client, works, page_size=50)
    assert works[10].author_qids == {"Q34943"}
    assert works[11].author_qids == {"Q34943"}
    assert any(q.startswith("DISTINCT Any W,P") for q in client.queries)
