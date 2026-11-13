# Plan for data/texts.cex (2026-11-13)

User spec: `data/texts.cex`, pipe-delimited, header `biblissima|urn|group|work`.
- `biblissima`: Biblissima's unique identifier (taken to be the Work ark `ark:/43093/oedata...`, since URNs are work level; CONFIRM).
- `urn`: CTS URN at WORK level with trailing colon: `urn:cts:greekLit:tlg0363.tlg001:` (5 colon-separated components, passage empty, so 4 colons; Perseus often omits the trailing colon).
- `group`: text group name (e.g. "Ptolemy" for `urn:cts:greekLit:tlg0363:`). `work`: work name (e.g. "Almagest" for `...tlg0363.tlg001:`).
- Cross-index of texts and manuscripts: the user will specify later.

## Method (heuristic matching; no Biblissima <-> CTS mapping exists in the data)
1. CTS catalogue from `__cts__.xml` metadata files of the Perseus/OGL repos (canonical-greekLit, canonical-latinLit, First1KGreek), sparse-cloned into `data/cts-sources/` (gitignored).
   textgroup file: `ti:textgroup@urn` + `ti:groupname` (multilingual); work file: `ti:work@urn`, `ti:title` (multilingual). Parse with stdlib ElementTree.
2. Biblissima side (portal RQL): Works (ark, displayed_title "Author (dates) : Title"), Work preferred_form / other_forms Designations (multilingual titles), authors via Text contributions (role "Auteur du texte") and Person forms.
3. Match author -> text group (normalised names, accents/case/punctuation folded), then title -> work within the group. Output only confident matches; keep a review list of near misses out of texts.cex.
4. Write texts.cex with sanitised fields, atomic write, same conventions as mss.cex; add tests with small CTS fixtures.
Expected coverage: classical / patristic Greek and Latin works only; most medieval vernacular works will have no URN.

## CTS catalogue as fetched (2026-11-13; data/cts-sources/)
- 2,802 `__cts__.xml` files: First1KGreek 1,467, canonical-greekLit 926, canonical-latinLit 409. All parse. 432 text groups, 2,188 works (greekLit 1,837, latinLit 350, hebrewlit 1). 36 groups / 93 works appear in >1 repo (merge by URN).
- Format confirmed: `ti:textgroup@urn` + `ti:groupname@xml:lang`; `ti:work@urn@groupUrn` + `ti:title@xml:lang`. URNs in the files have NO trailing colon (add it).
- Title languages: lat 1651, eng 582, grc 77, mul 11. Group name languages: eng 252, lat 216, plus a few mul/en/fre. Names differ across repos for 13 groups (e.g. tlg0059 "Plato"; tlg1311 "Didache" vs "Anonymous").
- Ptolemy: group urn:cts:greekLit:tlg0363 is named "Claudius Ptolemaeus" (lat) in both repos, NOT "Ptolemy". Almagest = tlg0363.tlg001, only in First1KGreek, titled "Syntaxis mathematica" (lat), no English "Almagest". Tetrabiblos = tlg007 ("Tetrabiblos" eng in canonical-greekLit; "Apotelesmatica (= Tetrabiblos)" lat in First1K); tlg011 "Musica".
- Name policy needed for `group` / `work` columns (default proposal: eng, then lat, then any).
- The catalogue is small (2,188 works), so expected texts.cex size is at most a few thousand rows.

## Discovery on Biblissima works (2026-11-13; samples/works/)
- Work.displayed_title is usually "Author (dates) : Title" (e.g. "Claude Ptolémée (0100?-0170?) : Harmoniques", "Homère : Odyssée") but anonymous-titled works exist ("Almageste", wiki-style preferred form, lang fr, source data.biblissima).
  The Almagest is Work eid 722489, title "Almageste" (no author prefix); its author comes from Text contributions (role "Auteur du texte", Person 136883 = "Claude Ptolémée (0100?-0170?)").
- Person 136883 links (same_as): Wikidata Q34943, GND 118641786, BnF, IdRef, LoC, BNE, Biblissima Q3210... Other Ptolemy persons: 136412 (auteur prétendu), 506245 Pseudo-Ptolemaeus, kings Ptolémée I-XV.
- French title "Almageste" will NOT string-match CTS "Syntaxis mathematica": such cases need Biblissima alternative forms (other_forms) or manual aliases. `almagest_other_forms` query failed (my typo: stray variable).
- Homère works exist ("Odyssée", hymns, Batrachomyomachie); Virgile: "Opera" only.
- Wikidata: the author numbers are TLG author ID and PHI Latin Texts author ID; TLG number = CTS greekLit group (tlg0363), PHI number = latinLit group (phi0690).
  CORRECTION (2026-11-13): the property numbers P1041 / P1055 / P8311 I first quoted came from a search result for kg.jstor.org and citygraph.abudhabi.nyu.edu, which are OTHER Wikibase instances with their own numbering. On Wikidata P1055 is something else (NLM id-like values) and P1041 holds items. Real Wikidata property numbers are still to be found (query the Wikidata SPARQL endpoint by label).

## Implemented (2026-11-13)
- `cts.py` (catalogue parser, URN normalisation with trailing colon, name policy eng > lat > mul > grc > fre), `wikidata.py` (loads a saved SPARQL result: Wikidata item -> group URNs),
  `texts.py` (fold/similarity, author->group->title matching, threshold + review split, portal readers `fetch_works` / `attach_authors`, writers), CLI `biblissima texts`.
- Works -> authors path (portal): `DISTINCT Any W,P ... WHERE T work W, K book T, K contributor P, K role R, R name "Auteur du texte", P is Person`; Person -> Wikidata via `P same_as E, E uri LIKE "%wikidata.org/entity/Q%"`; titles via Work preferred_form / other_forms Designations.
  UNTESTED LIVE: `DISTINCT Any` with ORDERBY/LIMIT/OFFSET; `E uri LIKE` inside a paged query; Work/Person joins at scale.
- Needs a saved Wikidata result (user runs a SPARQL query once). 57 tests pass (stdlib shim). Test fixtures include 5 real `__cts__.xml` files (Perseus / OGL metadata) in src/tests/data/cts.
- Output: data/texts.cex (confident matches only, header biblissima|urn|group|work) and data/texts_review.cex (score, label; not part of texts.cex).

## First live run (2026-11-13): zero matches, and why
- data/texts.cex and data/texts_review.cex contained only headers. Offline diagnosis from the cache (.cache/biblissima): 25,079 works, all with alternative forms;
  12,890 works have an author with a Wikidata link (2,115 distinct Wikidata authors); 0 of those authors appear in data/wikidata_tlg_phi.json (35,979 rows: 169 with ?tlg, 35,810 with ?phi).
- Cause: wrong Wikidata property numbers (see correction above). ?tlg values were item URLs, ?phi values looked like unrelated identifiers (e.g. 9889800).
- Fixes made: wikidata.py rejects results whose author numbers are not plain digit strings; the CLI now stops with an error when no work has an author in a CTS group instead of writing empty files.
- Next: find the right Wikidata properties (SPARQL by label), re-run the Wikidata query, then re-run the match (portal responses are cached, so the re-run is fast).

## Correct Wikidata properties (found 2026-11-13 via SPARQL by label; data/wikidata_properties.csv)
- P3576 TLG author ID; P6941 PHI Latin Texts author ID; P8311 PHI Latin Texts work ID; P7041 Perseus author ID.
- No Wikidata property for CTS URNs and none for "TLG work ID" was found by the label search.
- Corrected query: `SELECT ?p ?tlg ?phi WHERE { { ?p wdt:P3576 ?tlg } UNION { ?p wdt:P6941 ?phi } }` (now `biblissima.wikidata.SPARQL_QUERY`).
