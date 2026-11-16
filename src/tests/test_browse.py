from biblissima.browse import (
    ALL,
    NO_COLLECTION,
    VIEWER,
    portal_url,
    collection_options,
    collection_work_options,
    entries_for_collection,
    manuscript_collections,
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


def test_collection_menus():
    holders = manuscript_collections(MSS)
    assert holders == {"m1": "BnF", "m2": NO_COLLECTION}
    # m3 has no mss row, so it has no collection and is left out
    assert collection_options(INDEX, holders) == {
        "(none recorded) (1 MS)": NO_COLLECTION,
        "BnF (1 MS)": "BnF",
    }
    opts = collection_work_options("BnF", INDEX, TEXTS, holders)
    assert list(opts.items()) == [
        ("All (1 work in 1 manuscript)", ALL),
        ("Ptolemy - Syntaxis (1 MS)", "urn:cts:greekLit:tlg0363.tlg001:"),
    ]
    opts2 = collection_work_options(NO_COLLECTION, INDEX, TEXTS, holders)
    assert opts2["All (2 works in 1 manuscript)"] == ALL
    assert collection_work_options("Nowhere", INDEX, TEXTS, holders) == {
        "All (0 works in 0 manuscripts)": ALL
    }


def test_entries_for_collection():
    one = entries_for_collection("BnF", "urn:cts:greekLit:tlg0363.tlg001:", INDEX, TEXTS, MSS)
    assert len(one) == 1 and one[0]["locations"] == ["1-9", "20-30"]
    assert one[0]["collection"] == "" and "works" not in one[0]
    assert one[0]["manifests"] == ["http://a/1.json", "http://b/1 x.json"]
    allw = entries_for_collection(NO_COLLECTION, ALL, INDEX, TEXTS, MSS)
    assert allw[0]["works"] == [
        ("Ptolemy - Syntaxis", []),
        ("Ptolemy - Tetrabiblos", ["7"]),
    ]
    assert entries_for_collection("BnF", "urn:cts:greekLit:tlg0363.tlg007:", INDEX, TEXTS, MSS) == []


def test_render_per_work_lines():
    allw = entries_for_collection(NO_COLLECTION, ALL, INDEX, TEXTS, MSS)
    out = render_manuscripts_html(allw)
    assert "<div>Ptolemy - Tetrabiblos &mdash; 7</div>" in out
    assert "<div>Ptolemy - Syntaxis</div>" in out


def test_portal_link():
    assert portal_url("ark:/43093/mdata09ab") == "https://portail.biblissima.fr/ark:/43093/mdata09ab"
    entries = [{"ark": "ark:/1", "label": "A", "collection": "", "locations": [], "manifests": []}]
    out = render_manuscripts_html(entries)
    assert "<strong>A</strong>" in out and "</a><strong>" not in out
    assert 'href="https://portail.biblissima.fr/ark:/1"' in out
    assert "View Biblissima &#9656;</a>" in out and "background:#1a5fb4" in out
