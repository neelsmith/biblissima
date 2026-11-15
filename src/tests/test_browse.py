from biblissima.browse import (
    VIEWER,
    group_options,
    manuscript_counts,
    manuscripts_for_work,
    render_manuscripts_html,
    viewer_url,
    work_options,
)

TEXTS = [
    {"biblissima": "w1", "urn": "urn:cts:greekLit:tlg0363.tlg001:", "group": "Ptolemy", "work": "Syntaxis"},
    {"biblissima": "w2", "urn": "urn:cts:greekLit:tlg0363.tlg007:", "group": "Ptolemy", "work": "Tetrabiblos"},
    {"biblissima": "w3", "urn": "urn:cts:greekLit:tlg0012.tlg001:", "group": "Homer", "work": "Iliad"},
]
INDEX = [
    {"mss": "m1", "text": "urn:cts:greekLit:tlg0363.tlg001:", "location": "1-9"},
    {"mss": "m1", "text": "urn:cts:greekLit:tlg0363.tlg001:", "location": "20-30"},
    {"mss": "m1", "text": "urn:cts:greekLit:tlg0363.tlg001:", "location": "1-9"},
    {"mss": "m2", "text": "urn:cts:greekLit:tlg0363.tlg001:", "location": ""},
    {"mss": "m3", "text": "urn:cts:greekLit:tlg0363.tlg001:", "location": "5"},  # no manifest
    {"mss": "m2", "text": "urn:cts:greekLit:tlg0363.tlg007:", "location": "7"},
]
MSS = [
    {"biblissima": "m1", "label": "Zeta ms", "manifest": "http://a/1.json", "collection": "BnF"},
    {"biblissima": "m1", "label": "Zeta ms", "manifest": "http://b/1 x.json", "collection": "BnF"},
    {"biblissima": "m2", "label": "Alpha <ms>", "manifest": "http://a/2.json", "collection": ""},
]


def test_viewer_url():
    assert viewer_url("http://a/m.json") == VIEWER + "http://a/m.json"
    assert viewer_url(" http://a/m?x=1&y=2 ") == VIEWER + "http://a/m?x=1&y=2"
    assert viewer_url('http://a/b c"d') == VIEWER + "http://a/b%20c%22d"


def test_counts_and_menus():
    counts = manuscript_counts(INDEX)
    assert counts["urn:cts:greekLit:tlg0363.tlg001:"] == 3
    assert list(group_options(TEXTS)) == ["Homer (1 work)", "Ptolemy (2 works)"]
    assert group_options(TEXTS)["Ptolemy (2 works)"] == "Ptolemy"
    opts = work_options(TEXTS, "Ptolemy", counts)
    assert opts == {
        "Syntaxis (3 MSS)": "urn:cts:greekLit:tlg0363.tlg001:",
        "Tetrabiblos (1 MS)": "urn:cts:greekLit:tlg0363.tlg007:",
    }
    assert list(work_options(TEXTS, "Homer", counts)) == ["Iliad (0 MSS)"]


def test_duplicate_work_labels_are_disambiguated():
    texts = [
        {"biblissima": "a", "urn": "u:1:", "group": "G", "work": "W"},
        {"biblissima": "b", "urn": "u:2:", "group": "G", "work": "W"},
    ]
    assert len(work_options(texts, "G", {})) == 2


def test_manuscripts_for_work():
    entries = manuscripts_for_work("urn:cts:greekLit:tlg0363.tlg001:", INDEX, MSS)
    assert [e["ark"] for e in entries] == ["m2", "m1"]  # "" collection sorts first
    m1 = entries[1]
    assert m1["locations"] == ["1-9", "20-30"]
    assert m1["manifests"] == ["http://a/1.json", "http://b/1 x.json"]
    assert entries[0]["locations"] == []
    assert manuscripts_for_work("urn:none:", INDEX, MSS) == []


def test_render_html_escapes_and_links():
    entries = manuscripts_for_work("urn:cts:greekLit:tlg0363.tlg001:", INDEX, MSS)
    out = render_manuscripts_html(entries)
    assert "Alpha &lt;ms&gt;" in out
    assert f'href="{VIEWER}http://a/2.json"' in out
    assert "View images 1 &#9656;</a>" in out and "View images 2 &#9656;</a>" in out
    assert "background:#1a5fb4" in out
    assert "location: 1-9; 20-30" in out
    assert "http://b/1%20x.json" in out
