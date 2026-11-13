> SUPERSEDED by 07-implementation-plan.md (2026-11-08). Kept for history.

# Plan (no code written yet)

Packaging: `uv` project, `pytest`, Sphinx for API docs (autodoc/autosummary; furo or
sphinx-rtd theme; build in CI). marimo notebooks in `marimo/`. Source in `src/biblissima/`.
Do NOT edit README.md, docs/, quarto/, releases.md, datareleases.md, data-version.txt.
DECIDED (user, 2026-11-08): Sphinx sources live in `src/docs/` (top-level `docs/` stays user-owned).
DECIDED: Wikibase API is the access route (no SPARQL); design the client around it.

## Phase 0: Discovery (needs live access; see 01-data-sources.md)
1. Get access route settled (SPARQL access request / browser session / dump).
2. Via the Wikibase API (`wbsearchentities` type=property; `wbgetentities`) list properties and
   find the IDs in "Unknowns" #1. Inspect a few manuscripts known to have digitisations.
3. Record the verified model in `notes/03-data-model.md`; save a few raw JSON entity
   samples as test fixtures (small ones) for offline tests.

## Task 1: manuscripts that have IIIF manifests
- Preferred (if SPARQL available): select manuscript items that have the manifest
  statement; return QID, label, institution, shelfmark, manifest URL(s).
- Fallback (API only): `list=search` with `haswbstatement:P<manifest>` (CirrusSearch, if
  enabled; UNVERIFIED) or enumerate manuscript items (`haswbstatement:P31=Q<manuscript>`),
  then batch `wbgetentities` (50 ids) and filter locally. Page via `sroffset`/continue.
- Handle: multiple manifests, manifests on component or digital-copy items, v2 vs v3
  manifests, duplicates, malformed URLs.
- Validate: compare counts across two routes; spot-check manifest URLs resolve (optional,
  separate slow step); compare with the portal's `/iiif/collection/...` for a sample.

## Task 2: works and expressions in each manuscript
- Follow the verified "manuscript -> contains" property to expression items, then
  expression -> work (property TBD). Return rows:
  manuscript QID, expression QID/label, work QID/label, author, locus.
- Decide handling for manuscripts with several components/parts, and for texts without
  an expression (work only).
- Process in chunks keyed by the Task 1 manuscript list; cache raw entity JSON on disk.
- Final join: manuscript -> manifests -> (expression, work).

## Library design
- `client` (HTTP, User-Agent, retries/backoff, throttling, on-disk cache), `queries`
  (SPARQL builders and API helpers), `models` (typed dataclasses: Manuscript, Manifest,
  Expression, Work), `export` (pandas/CSV/JSON).
- Tests: pytest, unit tests on recorded fixtures (no network by default); marker `live` for
  opt-in integration tests; coverage target set once scaffolding exists.
- Docs: Sphinx autodoc from docstrings.

## Proposed order of work
1. Settle access and Sphinx location (user input).  2. Discovery + data-model note.
3. `uv init` scaffold, CI-less tooling, client + fixtures.  4. Task 1.  5. Task 2.
6. marimo notebooks, docs build.

## Open questions for the user
- Does a browser (the built-in one) reach data.biblissima.fr past the anti-bot check?

## REVISION 2026-11-08 (after live exploration)
- Task 1 is feasible with the Wikibase API: `list=search&srnamespace=120&srsearch=haswbstatement:P2=Q32810 haswbstatement:P196` (162,779 manuscripts),
  paged with sroffset, then batched `wbgetentities` (50) for P196 (+P191 qualifier), P195, P194, P129. Search offset limits (CirrusSearch max ~10,000 results per query)
  may require partitioning the query, e.g. by P194 collection or by id ranges. TO TEST.
- Task 2 is BLOCKED on a data source: Wikibase manuscripts have no text links. Candidate sources: (a) Portail Biblissima manuscript pages/API (need format);
  (b) external catalogues via identifiers (Jonas, Pinakes, Bibale, etc.); (c) a Wikibase relation from work side not yet found. Decide with user.
