# CTS URNs for texts: findings (2026-11-13; samples/cts/)

## Is there a CTS URN in Biblissima data? Not directly found.
- Wikibase: none of the 365 property labels mentions CTS / Perseus / canonical citation. Nearest: P145 Pinakes, P140 Jonas, P358 Comparatio oeuvres, P393 ThEMA, P382 BiblIndex, P356 Repertorium biblicum Medii Aevi.
- Portal: Work --same_as--> ExternalUri (uri). 16,910 same_as links on 10,057 of 25,079 works. First 3,000 links (ordered by work eid, so biased to the oldest works) by host:
  data.biblissima.fr 1417 (Wikibase items), data.bnf.fr 754, d-nb.info (GND) 307, id.loc.gov 242, idref.fr 154, datos.bne.es 43, jonas.irht.cnrs.fr 34, repbib.uni-trier.de 17,
  pinakes.irht.cnrs.fr 17, wikidata.org 10, geschichtsquellen.de 4, mgh.de 1. No Perseus / CTS hosts in this sample. Remaining 13,910 links not yet inspected.
- `LIKE` combined with `COUNT` on ExternalUri gave HTTP 500 (server error "list has no attribute rows"): count by paging instead.
- Text.repertory is empty for 59,715 of ~67k texts; filled values look like "BHG : 1318" (Bibliotheca hagiographica graeca numbers). No CTS.
- Text titles are free strings (e.g. fabliaux titles); Work.internal_id is a hash for some works.

## Possible routes (unverified)
1. Scan all 16,910 Work same_as links for hosts (cheap; 6 pages of 3,000). Wikidata links might lead to identifiers, but a Wikidata CTS property was not confirmed.
2. Match Works to the CTS registries by author + title: Perseus canonical repos (github.com/PerseusDL/canonical-greekLit, canonical-latinLit) and Open Greek and Latin carry `__cts__.xml` metadata
   with textgroup (author) and work titles. Only classical/patristic Greek and Latin works are covered; medieval vernacular works (e.g. fabliaux) will not match.
3. Authors: Biblissima Person records link to BnF / GND / VIAF / IdRef; author identity match first, then title match, would reduce false positives.
Sources: Perseus Catalog data URIs (sites.tufts.edu/perseuscatalog/?p=93), What is a CTS URN? (opengreekandlatin.org/?p=2813), github.com/PerseusDL/canonical.
