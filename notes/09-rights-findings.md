# Rights / credits for manifests: findings (2026-11-13; samples/rights/)

User decision: use Biblissima's own data (not each manifest's JSON) for `manifest_license` / `manifest_credits`.

## Harmless curl message
`curl: (23) Failure writing output` came from `curl | head -c 3000` (head closed the pipe). The 3,000-byte manifest sample was saved correctly.

## Portal `Database` entities do NOT describe manifests
- Only 62 Database entities; every one of the 338,731 manuscripts has at least one (`M databases D`). Fields: name, preferred_label, licence ("Public Domain Mark@en###Marque du Domaine Public@fr" style,
  language-tagged, `###`-separated), licence_website, usage_conditions (URL), operator. Many have no licence (Gallica, Pinakes, BnF, Jonas, e-codices-less...).
- They describe the DATA SOURCES (catalogues/libraries) that contributed to the manuscript record, not the digitisation behind a given manifest.
- Pal.gr.348 counter-example: its Databases are Heidelberg (licence Public Domain Mark, CC PDM URL) and Pinakes (no licence); but the manifest in P196 / mss.cex is the VATICAN one
  (https://digi.vatlib.it/iiif/MSS_Pal.gr.348/manifest.json), whose own JSON says `"attribution": "Images Copyright Biblioteca Apostolica Vaticana"`.
  Attaching "Public Domain Mark" to the Vatican manifest would be WRONG. So `M databases D` must not be used naively for manifest rights.

## Wikibase has the right link: P196 qualifier P191 (digital library)
- Q103733 (Pal.gr.348): P196 (manifest) carries qualifiers P191 = Q78787 and P279 (digitisation type) = Q120863. Both P197 (digitisation URLs: Heidelberg and Vatican) also carry P191 and P279.
- Digital library items, e.g. Q32814 Gallica: P2 = Q32805 and Q313297; P188 site officiel; P200 opérateur (Q32811 = BnF); P366 URL des conditions d'utilisation
  (https://gallica.bnf.fr/edit/und/conditions-dutilisation-des-contenus-de-gallica); P193 conforme à (Q32808 = IIIF); P187 licence is available as a property (not on Gallica).
- So per manifest: P191 -> digital library item -> {label, P200 operator label, P366 conditions URL, P187 licence}.
  Credits could be "<digital library> (<operator>)"; license could be the licence label if P187 exists, else the P366 conditions URL.
- Cost: reach Wikibase items for the manuscripts. Wikibase search cannot page past ~10,000 hits per query (CirrusSearch window, TO CONFIRM), so enumeration should come from the portal;
  the portal manuscript has a Record whose url is `https://data.biblissima.fr/entity/Q...` (seen on Pal.gr.348), giving the QID. Then `wbgetentities` 50 ids per call: ~3,300 calls for 162k manuscripts (~1 hour at 1 req/s).
- Cheaper alternative: map manifest host -> digital library (P188 / P189 URLs of the ~dozens of digital library items). Coarser; hosts shared by several libraries would be ambiguous.

## Open questions
- Is `ExternalUri.source` (portal) the digital library name for a manifest? (test below)
- Number and shape of digital library items (P2 = Q313297 / Q32805), and how many have P187 / P366.
- How many portal manuscripts carry the Wikibase-entity Record.


## Discovery results (2026-11-13, samples/rights2/) and decision
- `ExternalUri.source` is null for all 194,485 manifests: the portal does not say which library provides a manifest.
- Portal -> QID: 336,419 of 338,731 manuscripts have a record URL `https://data.biblissima.fr/entity/Q...` (Pal.gr.348: Q103733).
- Digital library items: class Q32805 "bibliothèque numérique" has 339 items; Q313297 "jeu de données" 61. Of 140 fetched: P188 site 136, P200 operator 125, P187 licence 43, P366 conditions URL 5.
  Licence items seen: Q32797, Q32799, Q32800, Q32801, Q32802, Q32803, Q32804, Q32807, Q228208 (labels resolved at run time).
- DigitVatLib (Q78787): operator Q32956 (Vatican. Biblioteca apostolica vaticana), site https://digi.vatlib.it, NO licence, no conditions URL.
- Decision: implemented per-manifest lookup via Wikibase P196[P191] (exact), see 08-scaffold.md update.
- Possible later improvement for blank licences: fall back to the manifest's own `license`/`attribution` (e.g. Vatican: "Images Copyright Biblioteca Apostolica Vaticana").
