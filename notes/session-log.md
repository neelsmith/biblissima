# Session log

## 2026-11-08 (session 1): scoping, no code
Done
- Read CLAUDE.md, README.md, releases.md, datareleases.md. Repo is a bare scaffold
  (one "Initial commit"; src, marimo, notes, docs, quarto all empty).
- Read doc.biblissima.fr/api pages (index, sparql, api-presentation, api-mediawiki,
  interface-donnees-liees). Findings in `01-data-sources.md`. Plan in `02-plan.md`.
- Decisions from user: "texts" = both works and expressions; tooling = uv + pytest;
  docs = Sphinx (tentative).

Findings that change the plan
- Data is Wikibase (data.biblissima.fr), NOT the older CubicWeb/CIDOC-CRM model.
- Public SPARQL endpoint does not exist yet (access by request).
- data.biblissima.fr uses an Anubis anti-bot challenge; the sandbox shell and the
  user's device shell both got proxy 403, so no live queries have been run.

Not done / unverified
- No property/item IDs known. No live API call has succeeded.

Next steps
1. User: request SPARQL access and/or test browser access; answer open questions in 02-plan.md.
2. Discovery phase, then record `03-data-model.md`.
3. Scaffold with `uv init`, then implement Task 1 and Task 2.
Files touched: notes/01-data-sources.md, notes/02-plan.md, notes/session-log.md only.

## 2026-11-08 (session 1, later)
- Decisions: Wikibase API is the route; Sphinx docs in `src/docs/`.
- Added `03-browser-checklist.md` for the user's interactive checks at data.biblissima.fr.
- Next: user returns results from the checklist; then discovery notes (`04-data-model.md`) and scaffold.

## 2026-11-08 (session 1, later still)
- User confirmed api.php works in browser and curl; saved `notes/bibquery.json` (siteinfo).
  Verified CirrusSearch + WikibaseCirrusSearch present; ~887k pages. Recorded in 01-data-sources.md.
- Next: property list, class Q-IDs, sample items, haswbstatement test (checklist items 2-6).
- Read keyword-search samples; found P196 (manifeste IIIF), Q32810 (manuscrit), Q282950 (œuvre). Need property labels,
  instance-of property id, expression class, and a haswbstatement:P196 test.
- Got property labels (04-property-labels.md): P2 instance of, P196 manifest, P195 cote, P169/P170 part/comprend, P354 auteur, P359 present in work.
  haswbstatement:P196 returned 0 with default namespace; retry with srnamespace=120. Class items Q32810/Q282950 sampled: sparse.
- Verified: srnamespace=120 works; P196 manifest on 174,678 items; 341,828 manuscripts (P2=Q32810). Manifest has P191 qualifier.
  No manuscript->text link found yet; P170/P359 are not it. Next: combined counts and entity labels for linking properties.
- Counts: 162,779 manuscripts have P196. No manuscript->text link via P170/P169/P359 (0). 8,706 work items (P2=Q282950).
  Portal page unreadable to Claude (Anubis); asked user to inspect it for JSON/RDF and visible text lists.
- Sampled works/attested/non-manuscript items. Wikibase manuscripts carry no text statements: Task 2 needs another source. Task 1 plan firmed (162,779 manuscripts; search-limit partitioning to test).
- Parsed user's saved portal page (05-portal-manuscript-page.md): texts live on the Portail (tdata/oedata entities, from Pinakes/Heidelberg), not in Wikibase.
  Moved the HTML to samples/portal_mdata60119c63_Pal.gr.348.html. Next: test curl/machine-readable views on the portal, ask Biblissima team.
- Portal tests: plain curl works; vid=ejsonexport returns entity attributes only (no relations); rdf/ntriples/content negotiation don't work. Next: test RQL via /view?rql=... and /schema.
- BREAKTHROUGH: portal RQL endpoint (/en/view?rql=...&vid=jsonexport) is public. 338,731 manuscripts. Schema in 06-portal-rql-schema.md:
  Manuscript has_part Component related_text Text work Work; Manuscript manifests Manifest. Next: attribute names, counts, Pal.gr.348 test, pagination limits.
- Verified portal chain with Pal.gr.348: 1 component, 1 text, 1 work, 1 manifest. Counts: 338,731 MS / 766,813 components / 67,274 texts / 25,079 works / 194,485 manifests.
  Large responses truncate at ~168 KB: paginate. COUNT(DISTINCT) over joins returned []. Heidelberg contents lines are not Texts (probably Notes).
- Round 3: 156,428 MS with manifest (portal) vs 162,779 (Wikibase); 57,399 MS with text at depth 1; 313,806 nested components; 21 orphan texts.
  Heidelberg contents are Notes (scopecontent). Invalid RQL returns []. Paging syntax and contributions still to fix.
- Round 4: paging verified (LIMIT after ORDERBY, before WHERE; 5,000 rows OK; deep offset OK). Text depth: depth1 57,399 MS, depth2 478 MS, none deeper.
  Authors hang off Text via Contribution (duplicates; group by role name). Wrote 07-implementation-plan.md (supersedes 02-plan.md). No code written yet.
  Next: user reviews plan, checks terms of use; then scaffold with uv.

## 2026-11-13 (session 1 continued)
- User judged the terms-of-use question acceptable (Biblissima tracks per-source rights). Claude could not read the mentions-legales page (Anubis); recorded in 07-implementation-plan.md.
  Design note: keep per-record source and licence (Database.licence etc.) in harvested data. Awaiting go-ahead to scaffold with uv.
- Read the saved mentions-legales page: legal notice only (rights reserved, credit source and rights holder, no open licence, nothing on automated access).
  Recommendation recorded: library ships no data, per-record attribution, ask the team about programmatic use before publishing any dataset. Awaiting user's decision/go-ahead.

## 2026-11-13 (session 1, scaffold)
- Scaffolded uv project (see 08-scaffold.md): client, rql paging, manifest harvest, mss.cex writer, CLI, 29 tests (pass under a stdlib shim; pytest not available here), Sphinx skeleton in src/docs.
- mss.cex header used: biblissima|label|manifest|manifest_license|manifest_credits (request had a duplicate `manifest` and a bare `credits`; to confirm).
- Not yet run live. manifest_license / manifest_credits empty pending a decision on the rights source.
- Next: user runs `uv sync --group dev && uv run pytest`, then `uv run biblissima mss --limit 20 ...`; run rights discovery queries; choose rights source.
- Rights: portal Database entities (62) describe data sources, not manifests; Pal.gr.348 shows a mismatch (Heidelberg PDM vs Vatican manifest). Better link: Wikibase P196 qualifier P191 -> digital library item
  (P366 conditions URL, P200 operator, P187 licence). Wrote 09-rights-findings.md. Next: discovery on digital library items, ExternalUri.source, portal->QID records.
- Implemented rights lookup (Wikibase P196[P191] -> digital library: operator, licence, conditions URL); refactored client (HttpClient, shared Throttle, WikibaseClient);
  new modules rights.py, harvest.py; CLI --no-rights. 42 tests pass under the stdlib shim. Not run live. Next: user runs `uv run pytest`, then `biblissima mss --limit 20` and inspects rights columns.
