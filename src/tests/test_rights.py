from biblissima.rights import Library, RightsResolver, label_of, snak_value

from conftest import FakeWikibase

LIB_VAT = "Q78787"
LIB_ARCA = "Q78745"


def item(qid):
    return {"snaktype": "value", "datavalue": {"value": {"id": qid}}}


def claim(value, qualifiers=None, rank="normal"):
    snak = {"snaktype": "value", "datavalue": {"value": value}}
    c = {"mainsnak": snak, "rank": rank}
    if qualifiers:
        c["qualifiers"] = qualifiers
    return c


def item_claim(qid, **kw):
    return claim({"id": qid}, **kw)


def manuscript(*manifests):
    """manifests: (url, [library qids])"""
    return {
        "claims": {
            "P196": [
                claim(url, {"P191": [item(lib) for lib in libs]} if libs else None)
                for url, libs in manifests
            ]
        }
    }


def entities():
    return {
        "Q1": manuscript(("http://vat/m.json", [LIB_VAT])),
        "Q2": manuscript(("http://arca/m.json", [LIB_ARCA]), ("http://other/m.json", [])),
        LIB_VAT: {
            "labels": {"en": {"value": "DigitVatLib"}},
            "claims": {"P200": [item_claim("Q32956")]},
        },
        LIB_ARCA: {
            "labels": {"fr": {"value": "ARCA"}},
            "claims": {
                "P200": [item_claim("Q32914")],
                "P187": [item_claim("Q32800")],
                "P366": [claim("https://arca.irht.cnrs.fr/mentions_legales")],
            },
        },
        "Q32956": {"labels": {"en": {"value": "Vatican. Biblioteca apostolica vaticana"}}},
        "Q32914": {"labels": {"en": {"value": "IRHT"}}},
        "Q32800": {"labels": {"en": {"value": "CC BY-NC"}}},
    }


def test_label_and_value_helpers():
    assert label_of({"labels": {"fr": {"value": "x"}, "en": {"value": "y"}}}) == "y"
    assert label_of({"labels": {"de": {"value": "z"}}}) == "z"
    assert label_of({}, "Q9") == "Q9"
    assert snak_value({"snaktype": "novalue"}) is None


def test_library_strings():
    lib = Library("Q1", "ARCA", ("IRHT",), ("CC BY-NC",), "http://terms")
    assert lib.credits == "ARCA (IRHT)"
    assert lib.license == "CC BY-NC; http://terms"
    assert Library("Q2", "Only label").credits == "Only label"
    assert Library("Q3", "x").license == ""


def test_resolver_follows_p196_p191_chain():
    r = RightsResolver(FakeWikibase(entities()))
    r.prefetch(["Q1", "Q2"])
    assert r.rights_for("Q1", "http://vat/m.json") == (
        "",
        "DigitVatLib (Vatican. Biblioteca apostolica vaticana)",
    )
    assert r.rights_for("Q2", "http://arca/m.json") == (
        "CC BY-NC; https://arca.irht.cnrs.fr/mentions_legales",
        "ARCA (IRHT)",
    )


def test_manifest_without_library_or_unknown_manuscript_is_blank():
    r = RightsResolver(FakeWikibase(entities()))
    r.prefetch(["Q2", "Q404"])
    assert r.rights_for("Q2", "http://other/m.json") == ("", "")
    assert r.rights_for("Q404", "http://x") == ("", "")
    assert r.rights_for("Q2", "http://not-in-wikibase") == ("", "")


def test_prefetch_does_not_refetch_and_batches():
    wb = FakeWikibase(entities())
    r = RightsResolver(wb)
    r.prefetch(["Q1"])
    calls = len(wb.calls)
    r.prefetch(["Q1"])
    assert len(wb.calls) == calls
    assert all(len(ids) <= 50 for ids, _ in wb.calls)


def test_deprecated_claims_are_ignored():
    ents = entities()
    ents["Q1"]["claims"]["P196"][0]["rank"] = "deprecated"
    r = RightsResolver(FakeWikibase(ents))
    r.prefetch(["Q1"])
    assert r.rights_for("Q1", "http://vat/m.json") == ("", "")
