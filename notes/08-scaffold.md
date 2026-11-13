# Scaffold (2026-11-13)

## Layout
- `pyproject.toml` (hatchling, src layout, `requests` dependency, dependency groups `dev` = pytest/pytest-cov, `docs` = sphinx/furo; CLI `biblissima`)
- `src/biblissima/`: `client.py` (PortalClient: throttle, retries, empty-result guard, JSON validation, optional disk cache), `rql.py` (quote, page_query, iter_rows),
  `manifests.py` (ManifestRecord, iter_manifest_records), `export.py` (HEADER, write_mss_cex), `cli.py` (`biblissima mss`)
- `src/tests/` (pytest; fake session/client in conftest.py; fixture `data/pal_gr_348_rows.json` built from the observed Pal.gr.348 row). Tests live in `src/` because CLAUDE.md says src is for code.
- `src/docs/` Sphinx (autodoc, furo). Build: `uv run --group docs sphinx-build -b html src/docs src/docs/_build/html`
- `.gitignore` ignores `data/` (harvested data is not committed until reuse rights are clarified), `.venv`, caches, Sphinx build.
- `data/` exists, empty.

## Run
```
uv sync --group dev
uv run pytest                       # 29 tests, no network
uv run biblissima mss --limit 20 --out data/mss_sample.cex --user-agent "biblissima-py (you@example.org)"
uv run biblissima mss --cache-dir .cache/biblissima --user-agent "..."   # full run, ~1 request/s, resumable via cache
```

## mss.cex
- Delimiter `|`, UTF-8, LF, csv-style quoting only when a field contains `|` or a quote. Header (5 columns):
  `biblissima|label|manifest|manifest_license|manifest_credits`
  The header in the request had 6 names (`...|manifest_license|manifest|credits`), apparently a typo; the described columns are these five. CONFIRM with user.
- `biblissima` = portal ARK (`ark:/43093/mdata...`), `label` = portal `displayed_title` with markup stripped, one row per (manuscript, manifest URL).
- `manifest_license` / `manifest_credits`: filled from Wikibase via P196 -> P191 digital library (see 09-rights-findings.md and the update at the end of this file); `--no-rights` leaves them empty.

## Verification
- pytest is not installed in Claude's sandbox and package installs are blocked, so tests were run with a stdlib shim (a tiny stand-in for `pytest.raises`): 29 passed.
  First run with real pytest should be done by the user (`uv run pytest`).
- NOT yet run against the live portal. First live run should be `--limit 20`. Untested assumptions: `ORDERBY M,U` (two sort keys) is accepted by the RQL parser;
  `displayed_title` / `ark` / `uri` attributes return plain strings in jsonexport (ark did in tests; displayed_title and uri did in earlier ejson/jsonexport tests).

## Open design question: where do license and credits come from?
1. From each IIIF manifest's own metadata (`license`/`rights`, `attribution`/`requiredStatement`): authoritative, but needs ~156k requests to hundreds of external servers (BnF, BAV, etc.).
2. From Biblissima's own data: portal `Database` entities (`licence`, `licence_website`, `usage_conditions`, `name`, `operator`) via `M databases D` or `Record`; or Wikibase P196's P191 qualifier -> digital library item (Q32814 etc.).
   Cheap, but coarse, and the link from a manifest to the right Database is unverified.
Discovery queries for option 2 are in the chat; results should go to `notes/samples/rights/`.


## Update 2026-11-13 (rights implemented)
- New: `HttpClient` base (+ shared `Throttle`) with `PortalClient` and `WikibaseClient` (`get_entities`, max 50 ids); `rights.py` (RightsResolver, Library); `harvest.py` (build_mss_records);
  `manifests.iter_qids` (portal record URL `https://data.biblissima.fr/entity/Q...` -> QID). CLI: default does rights; `--no-rights`, `--wikibase-url`.
- Flow: pass 1 portal (ark, QID) for manuscripts with manifests; pass 2 portal (ark, title, manifest URL); per 50 distinct QIDs one `wbgetentities(props=claims)`; then library items
  (labels+claims) and operator/licence labels, cached in memory. Match is by exact manifest URL; otherwise rights blank.
- Rights text: credits = "Library (operator / operator)"; license = licence label(s) then P366 URL, "; " joined. From the 140 library items fetched: P187 licence on 43, P366 on 5, P200 operator on 125.
  Pal.gr.348 would get credits "DigitVatLib - Biblioteca Apostolica Vaticana (Vatican. Biblioteca apostolica vaticana)" and an EMPTY license (Vatican library item has none).
- Cost of a full run: ~2 x 80 portal pages + ~3,300 Wikibase batches + ~10 more: roughly 1-1.5 hours at 1 request/s combined. Use `--cache-dir` so an interrupted run resumes.
- Tests: 42 pass under the stdlib shim (not yet under real pytest after this change). Not yet run live. Untested live: LIKE filter in the QID query combined with `ORDERBY MA,QU`; `wbgetentities` with `props=claims` for 50 ids; that portal manifest URLs equal Wikibase P196 URLs for most manuscripts.
- Known gap: only the first 100 of 339 `Q32805` digital library items were fetched in discovery (search window); the resolver fetches libraries on demand by QID, so this does not matter for the run.
- Counts from discovery: 336,419 of 338,731 manuscripts have a Wikibase record on the portal; `ExternalUri.source` is null for all 194,485 manifests (dead end).
