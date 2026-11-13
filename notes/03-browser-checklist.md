# Checklist: things to check interactively at data.biblissima.fr
Save raw outputs (or paste into chat). Small JSON samples can go in notes/samples/.

1. API reachable without a challenge?
   https://data.biblissima.fr/w/api.php?action=query&meta=siteinfo&siprop=general|statistics|extensions&format=json
   Note: does it return JSON in the browser? Does `curl -sS -A "biblissima-py-dev" <same url>` work from your own terminal?
   In the extensions list, is WikibaseCirrusSearch / CirrusSearch present (needed for haswbstatement:)?
2. Property list: Special:ListProperties. Need the P-IDs and labels for: instance of, shelfmark, holding
   institution, IIIF manifest / digital copy, contains text/expression, expression-of-work, author, folio/locus.
3. Class (Q) items for: manuscript, work, expression, (component/part, digital copy if they exist).
4. Example items: 2-3 manuscripts that have IIIF manifests, 2 expressions, 1 work. Open
   /w/Spécial:EntityData/Q<id>.json for each and save it.
5. Example SPARQL queries page (Project:SPARQL_examples): copy its text; it should reveal the IDs.
6. Search test: api.php?action=query&list=search&srsearch=haswbstatement:P<instance-of>=Q<manuscript>&srlimit=5&format=json
   Does it return hits, and how many in total (`searchinfo.totalhits`)?
7. Rough scale: item counts (Special:Statistics) and manuscript count, if visible.
8. Policy: any rate limits, User-Agent policy, terms of use, or a published data dump (ask the team if unclear).
