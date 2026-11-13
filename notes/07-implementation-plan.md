# Implementation plan (supersedes 02-plan.md; written 2026-11-08, no code yet)

## Decisions
- Primary source for BOTH tasks: Portail Biblissima RQL endpoint `GET https://portail.biblissima.fr/en/view?rql=...&vid=jsonexport` (see 06-portal-rql-schema.md).
  It holds manuscripts, manifests and the manuscript -> component -> text -> work chain.
- Secondary source: Wikibase API (data.biblissima.fr/w/api.php), used for cross-checking manifests (P196) and linking to authority items
  (portal ark `mdata...` == Wikibase P129). Not needed for the core harvest.
- Tooling: uv, pytest; Sphinx docs in `src/docs/`; marimo notebooks in `marimo/`; source in `src/biblissima/`; notes in `notes/`.
- Untouchable by Claude: README.md, docs/, quarto/, releases.md, datareleases.md, data-version.txt.

## Task 1: all manuscripts that have IIIF manifests
Query (keyset paging, ~5,000 rows/page, 1 s pause):
`Any M,MA,CT,U ORDERBY M LIMIT 5000 WHERE M is Manuscript, M > <last_eid>, M ark MA, M cote CT, M manifests X, X object_uri E, E uri U`
(add `OPTIONAL`-style follow-ups, e.g. a second query for title/institution (stored_at -> CorporateBody preferred_form), languages, dates).
- A manuscript with several manifests yields several rows: group by ark.
- Expected size: ~156,428 manuscripts (portal) vs 162,779 (Wikibase P196). Reconcile the ~6,000 gap: (a) manifests attached to Components only, (b) different imports,
  (c) items present in one source only. Report the gap in the library docs.
- Check Incunabula/other types separately (they also have manifests): expose `kind`.
- Validation: row counts vs `COUNT` queries; sampled manifest URLs equal Wikibase P196; optional (slow, off by default) manifest URL liveness check.

## Task 2: texts (expressions) and works in each manuscript
Texts attach to Components. Run two queries and union them:
- depth 1: `M has_part C, C related_text T`
- depth 2: `M has_part C1, C1 has_part C2, C2 related_text T`
Per page of manuscripts (by eid ranges): rows of (manuscript ark, component ark/type/order/minmax_folios, text ark/title/lang/repertory).
Then separate queries (batched by text eid ranges):
- `T work W` -> work ark, displayed_title, publication_year, lang (works are the abstract text; texts are the expressions in this manuscript)
- authors: `K is Contribution, K book T, K contributor A, K role R, R name RN, A preferred_form D, D title N`, DISTINCT, group by role name
- free-text contents notes: `C notes_scopecontent N` (HTML with titles and folio ranges, from sources like Heidelberg), kept as raw text in a separate field
- the source of each text: Record/Database link (Pinakes, Jonas, etc.) via `T records R` / ark prefix (`pardata...pinakes...`)
Edge cases: 21 orphan texts without a component (include in a separate list); manuscripts with no texts (281,332 of 338,731); components of type other than "textual";
duplicate contributions; Works without texts.
Expected scale: 57,399+ manuscripts with texts; 67,274 texts; 25,079 works.

## Library design
- `biblissima.client`: RQL over HTTP (User-Agent with contact, 1 s throttle, retries with backoff, timeouts); a guard for the silent-failure behaviour
  (`[]` for invalid RQL) using a known sentinel query; on-disk cache of raw pages for reproducible harvests.
- `biblissima.queries`: named, tested RQL builders (keyset paging; no string concatenation of untrusted input; escape quotes).
- `biblissima.models`: dataclasses Manuscript, Manifest, Component, Text, Work, Contribution.
- `biblissima.harvest`: iterators `manuscripts_with_manifests()`, `texts_for(manuscript)`, `harvest_all()`; exports to CSV/JSON/Parquet(if available).
- `biblissima.wikibase` (optional later): search `haswbstatement:` (srnamespace=120) and `wbgetentities` for cross-checks.
- Tests: pytest with fixtures from `notes/samples/` (copy a minimal set into `src/tests/data/`); `live` marker for opt-in network tests; coverage goal set at scaffold.
- Docs: Sphinx in `src/docs/` (autodoc + a data-model page derived from 06-portal-rql-schema.md).

## Politeness and risk
- Total harvest is a few hundred requests (338,731 manuscripts / 5,000 per page = 68 pages per query) plus text/work/author passes; keep ~1 request/s and cache.
- Confirm Terms of use (portail.biblissima.fr/en/mentions-legales) and inform team@biblissima-condorcet.fr; ask whether they would rather provide a dump.
- The RQL endpoint is undocumented: pin schema assumptions in tests and keep a schema-check function (CWRelation / CWAttribute queries) to detect changes.
- Unverified: server caps on LIMIT, whether `M > <eid>` keyset syntax is accepted (fall back to OFFSET, which works to 335,000).

## Proposed order of work
1. (User) Check terms of use; optional email to the team.  2. `uv init` scaffold, client + sentinel guard + fixtures + tests.
3. Task 1 queries/models/tests.  4. Task 2 queries/models/tests.  5. marimo notebooks.  6. Sphinx docs.  7. Reconcile with Wikibase.

## Terms of use / rights (2026-11-13)
- User's judgement: Biblissima is chiefly an aggregator that tracks the rights of each source carefully, so a gentle harvest of the public portal is judged acceptable.
- Claude could NOT read https://portail.biblissima.fr/en/mentions-legales (Anubis challenge for Claude's fetch tool). The challenge page itself says it exists to protect the
  server from aggressive scraping, and the site is `noindex,nofollow`. So keep the harvest light: identified User-Agent, ~1 request/s, cached pages, no parallel requests.
- TODO (user): paste or save the licence / reuse / attribution wording into `notes/samples/mentions-legales.txt`. The library docs and any exported dataset should state the
  data licence (the API docs say Licence Ouverte 2.0 for the referentials; per-source rights on the portal still to confirm, e.g. via `Database.licence`,
  `Database.licence_website`, `Database.usage_conditions` attributes, which exist in the portal schema) and carry per-record source attribution.
- Design consequence: harvested records keep their source (`Record.source`, `Database.name`, `Database.licence`) so reuse rights can be tracked per record.

### Read 2026-11-13: portal "Terms of use" (`samples/portail_mentions_legales.html`, French legal notice)
- It is a standard legal notice, NOT an open licence. Key points (paraphrased): the site's texts and illustrations are used with the agreement of rights holders and are protected by IP law;
  no right or licence to use them in any way without prior written agreement of the rights holders; only private-use copies and short quotations are allowed (CPI L122-5);
  any authorised reproduction or use must credit the source and the rights holder; information is provided "as is", the user is solely responsible for its use; Biblissima+ may
  change or suspend access at any time.
- It says nothing about automated access, APIs, rate limits, or data reuse/licensing.
- Contrast: the API docs (doc.biblissima.fr/api, updated 2024-05-21) state the Wikibase referentials data is under Licence Ouverte 2.0.
- Consequences for design (not legal advice): (1) the library ships code only, no harvested data; (2) harvested records keep source + licence attribution; (3) do not publish
  harvested portal datasets (datareleases.md) before the rights are clarified with the team; (4) prefer the Wikibase (Licence Ouverte 2.0) where it can answer the question (e.g. manifests via P196);
  (5) ask team@biblissima-condorcet.fr about permitted programmatic use of the portal RQL endpoint, and about a data dump.
