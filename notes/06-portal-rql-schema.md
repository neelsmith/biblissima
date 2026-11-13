# Portal (CubicWeb) RQL access and schema (2026-11-08)

## Access: WORKS from the user's terminal, no auth, no challenge
`GET https://portail.biblissima.fr/en/view?rql=<RQL>&vid=jsonexport|ejsonexport`
- jsonexport: rows as arrays of values (entities appear as eids). ejsonexport: entity objects with their attributes (no relations).
- Public schema pages also work: /en/schema, /en/schema/Manuscript (HTML, saved in samples/portal/rql/).
- Meta-schema queries work (CWEType, CWRelation, CWAttribute). `Any COUNT(X) WHERE X is Manuscript` -> 338,731.
- Raw data: samples/portal/rql/{etypes,relations}.json (96 entity types, 849 relation definitions).
- Etiquette: identify the client in User-Agent; throttle; paginate with LIMIT/OFFSET; confirm Terms of use (portail.biblissima.fr/en/mentions-legales) and
  tell the team. TO CHECK: server-side row limits, timeouts.

## Entity types of interest
Manuscript, Incunabula, MultiVolumeManuscript, Component, Text, Work, Manifest, DigitalSurrogate, ExternalUri, Designation, Database, Record, Note,
Contribution (role links person to Component/Text/Work), Person, CorporateBody, Collection, Edition, Descriptor.

## Relations (from relations.json)
- Manuscript --has_part--> Component   (Manuscript/Incunabula/Binding/Edition/Inscription all have has_part Component; Component has_part Component)
- **Component --related_text--> Text**   (also related_text_designation -> Designation, text_notes -> Note)
- **Text --work--> Work**; Text: title_forms -> Designation, incipit / explicit -> Note, textual_typology -> TextualTypology, databases -> Database, records -> Record
- Work: preferred_form / other_forms -> Designation, genre -> Genre, same_as -> ExternalUri, databases, records
- Manuscript --manifests--> Manifest (also Component, Incunabula, Edition, ... manifests -> Manifest); Manifest --object_uri--> ExternalUri; Manifest --iiif_features--> IIIFFeature
- Manuscript --digital_surrogates--> DigitalSurrogate --object_uri--> ExternalUri
- Manuscript: canonical_shelfmark / shelfmarks -> Shelfmark, stored_at / origin_repo -> CorporateBody, same_as -> ExternalUri (probably links to Wikibase Q ids), databases -> Database, volume_of -> MultiVolumeManuscript
- Contribution: book -> Component|Text|Work, role -> Role (+ person link TBD)
- Texts hang off **Component**, not directly off Manuscript (no Manuscript --related_text--> Text relation).
  So texts of a manuscript = Manuscript has_part Component related_text Text, possibly with nested components (Component has_part Component).

## Mapping to the user's goals
- Task 1 (manuscripts with IIIF): `Manuscript manifests Manifest` + Manifest.object_uri -> ExternalUri.uri (to verify attribute names), or the Wikibase route (P196).
- Task 2: works = Work entities; expressions = Text entities (the portal's "text in this manuscript"), `Text --work--> Work`.

## Verified (2026-11-08, samples/portal/rql2/)
Counts: Manuscript 338,731; Component 766,813; Text 67,274; Work 25,079; Manifest 194,485 (all manifest-bearing entity types, not only manuscripts).
`COUNT(DISTINCT M)` with relation joins returned `[]` (unsupported/failed); use another counting form (EXISTS) or paginate.

### Attributes (CWAttribute)
- Manuscript: ark, cote, displayed_title, lang, object_type, start_year, stop_year, usage_label, volume, extent, format, dimension_str, internal_id,
  bibrefs, bibrefs_from_wb, *_desc fields, digitized_url, json_meta, json_conflicts, creation/modification_date, cwuri
- Component: ark, type (e.g. "textual"), lang, order, minmax_folios, displayed_title, internal_id, extent, *_desc, digitized_url, ...
- Text: ark, title, displayed_title, displayed_title_en, lang, repertory, comment_lang, ...
- Work: ark, displayed_title, lang, publication_year, internal_id
- Manifest / DigitalSurrogate: object_type ("integral", ...) only; URL is via `object_uri -> ExternalUri.uri`
- ExternalUri: uri, source. Designation: title, lang, source. Record: source, source_uri, url. Database: name, preferred_label, dbid, wikibase_id, licence, url...
- Contribution: certainty; links: book -> (Manuscript|Component|Text|Work|...), contributor -> Person|CorporateBody, role -> Role, context -> Component. So authors of a text
  = `Contribution book Text, contributor Person, role Role`.
- Component --has_part--> Component also exists (nested components).

### Worked example: Pal.gr.348 (Manuscript eid 1025994)
- 1 Component (eid 4535859, type "textual", lang Grec, ark `ark:/43093/pardata66080pinakes8f05dfe6-...`; the "pardata...pinakes" ark shows the source = Pinakes)
- 1 Text (eid 3978443, title "Commentaire de l'Arithmétique de Nicomaque", ark tdata2f58a0bc...)
- 1 Work (eid 805864, "Jean Philopon (0490?-0566?) : Commentaire de l'Arithmétique de Nicomaque", publication_year 529, ark oedata24ff59...)
- 1 Manifest (eid 9344306, object_type integral); URI via object_uri->uri = https://digi.vatlib.it/iiif/MSS_Pal.gr.348/manifest.json
  (identical to Wikibase P196, good cross-check).
- The Heidelberg "contents" lines shown on the web page (folio ranges "1-159", "Liber I 1-92") are NOT a Text here: probably Notes
  (e.g. Component/Manuscript notes_scopecontent or text_notes). TO CHECK.

### Paging / limits
- `LIMIT 5 OFFSET 5` works. `LIMIT 100000` returned HTTP 200 but only 167,806 bytes (about 15,357 eids) and truncated, invalid JSON:
  the server (or a proxy) cuts large responses. => Always paginate in small pages (e.g. 1,000-5,000 rows) and validate that each page parses; order by eid for stable paging.

## Verified round 3 (2026-11-08, samples/portal/rql3/)
- Manuscripts with a manifest (portal): 156,428 (Wikibase P196 on P2=Q32810: 162,779; gap ~6,351, to be reconciled; sources differ).
- Manuscripts with at least one text via `has_part Component related_text Text` (depth 1 only): 57,399 of 338,731.
- Nested components: 313,806 components are themselves children of a Component (`has_part`), so texts may sit deeper; must test depth 2, 3, ...
- Texts not attached to any component: 21 (orphans).
- Query time ~0.5 s for simple, ~2.2 s for a join count: fine for polite paging.
- "Contents" lines on the web page (Heidelberg: language, "1-159 - Johannes, Philoponus: ...", "1-92 - Liber I") are stored as a Note reached
  via `Component notes_scopecontent` (HTML text with titles and folio ranges), on the Component (rql: `M has_part C, C notes_scopecontent N`; the test
  `M notes_scopecontent N` returned a note, the exact owner needs confirming). They are free text, not structured Text entities.
- Failed/invalid RQL returns HTTP 200 with `[]` (no error). Treat `[]` with care: validate queries on a known row. The paging test with
  `ORDERBY` placed before `WHERE` after `LIMIT`/`OFFSET` returned `[]` (probably wrong clause order: use `Any M,MA ORDERBY M LIMIT n OFFSET k WHERE ...`).
- Contribution query for Pal.gr.348's text returned `[]` (author may be attached to the Work, or the query was wrong).

## Verified round 4 (2026-11-08, samples/portal/rql4/)
- Correct clause order: `Any M,MA ORDERBY M LIMIT 5000 OFFSET 0 WHERE M is Manuscript, M ark MA`. (`LIMIT` at the END of the query silently returns `[]`.)
- Paging works: 1,000 rows (70 KB, 0.9 s), 5,000 rows (354 KB, 1.2 s), OFFSET 335000 gave the last 3,731 rows (total 338,731, matches COUNT).
  The earlier truncation at ~168 KB happened only for LIMIT 100000 (cause unknown: row or time cap). Use pages of 1,000-5,000.
- Nesting: texts via depth 2 (`M has_part C1, C1 has_part C2, C2 related_text T`): 478 manuscripts; depth 3: 0; depth-4 components: 0.
  So search texts at component depth 1 and 2 only (union). Depth-1: 57,399 manuscripts; depth-2: 478 (overlap with depth 1 unknown).
- Authors: for Pal.gr.348, `K book T, K contributor A` (T = the manuscript's Text) returns many Contribution rows all with contributor eid 125249 (Jean Philopon):
  likely duplicate contributions (one per source/role); need `K role R, R name RN` and DISTINCT. The same query on the Work returns `[]`, so authors hang off Text.
- Role vocabulary: 90 Role entities (`name`, `code`, e.g. "Auteur du texte" code 70/71 (two entities with the same name), "Copiste" 270, "Traducteur" 680, "Commentateur" 120,
  "Auteur commenté" (no code), "Ancien possesseur" 4010). Several roles share a name (e.g. many "Autre intervenant"), so group by name, not eid.
