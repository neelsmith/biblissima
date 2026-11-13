# Portail Biblissima manuscript page: structure (2026-11-08)
Source: user-saved HTML of https://portail.biblissima.fr/en/ark:/43093/mdata60119c636ac27834e52a0179c8baafd3a34857ed
(`samples/portal_mdata60119c63_Pal.gr.348.html`; Vatican, BAV, Pal.gr.348). The portal is a separate application from the Wikibase
(URLs like `bbma.view?vid=search-results&facet:etype-facet=Manuscript` suggest CubicWeb).

## What the page shows
- Header: Wikibase id link **https://data.biblissima.fr/entity/Q103733** ("Biblissima+ Identifier"), attested title, other labels, holding
  institution, languages, dates (each with its data source).
- **Digitisations**: IIIF manifest (here https://digi.vatlib.it/iiif/MSS_Pal.gr.348/manifest.json) and full-digitisation URLs.
- **Contents**, grouped by data source:
  - Source "Heidelberger historische Bestände – digital": text languages; titles with folio ranges
    ("1-159 - Johannes, Philoponus: In Nicomachi ... Commentarius", "1-92 - Liber I", "92-159 - Liber II").
  - **"Text in this manuscript"**, source "Pinakes": a text entity (ark `.../tdata2f58...`) with label, **"Related work"** (ark `.../oedata24ff...`)
    and "Auteur du texte" (person ark `.../pdata152a...`).
- Participants, former owner, "Formerly part of" (collection), bibliography (CSV export at /csv/bibref/<id>), data sources (Pinakes notice
  https://pinakes.irht.cnrs.fr/notices/cote/66080), other identifiers (BAV opac, Heidelberg URN).
- No export button for the manuscript itself (the "Exporter" button is commented out in the HTML). No JSON/RDF links in the HTML.

## Portal ark prefixes seen (ark:/43093/...)
mdata = manuscript; tdata = text in a manuscript (expression-like); oedata = work ("Related work"); pdata = person; cdata = organisation/institution;
coldata = historical collection; thb = iconographic thesaurus; idata = incunable (from Wikibase P129 values).
Wikibase P129 "identifiant Portail Biblissima" holds these mdata/idata/pdata ids, so a Wikibase item can be mapped to its portal page.

## Implication
Texts-in-manuscripts exist on the portal (from Pinakes, Heidelberg, etc.), keyed by the manuscript's ark (= Wikibase P129). Works (oedata) and texts (tdata)
map onto the user's "works and expressions" goal. Still needed: a machine-readable route to this data.

## To test (user's terminal)
- Does `curl` get the portal HTML, or an Anubis challenge?
- Does the portal honour `?vid=jsonexport|ejsonexport|rdf|ntriples|n3` or `Accept: application/rdf+xml|application/ld+json`?
- Wikibase item Q103733: does it hold any text statements?

## Results of portal format tests (2026-11-08, user's terminal; samples/portal/)
- Plain curl returns the HTML page (HTTP 200, no Anubis challenge from the user's terminal).
- `?vid=ejsonexport` -> JSON list with the entity's own attributes (cw_etype "Manuscript", eid 1025994, ark, cote, lang, start_year/stop_year,
  displayed_title, cwuri...). No relations (no texts) in this view.
- `?vid=jsonexport` -> `[[1025994]]` (just the eid). `?vid=rdf` -> HTTP 500; `?vid=ntriples` and `Accept: rdf/json-ld` -> ignored (HTML).
- Portal is CubicWeb (eids, cw_etype, ejsonexport). A CubicWeb site may accept RQL on `/view?rql=...&vid=ejsonexport|jsonexport`; and expose `/schema`. TO TEST.
- Wikibase Q103733 holds only: P2=Q32810, P195 cote, P194 collection (Q32956), P129 mdata ark, P145 Pinakes id (cote/66080), P197, P353, P196 manifest, P218, P379.
  No text statements, confirming texts come from the portal.
