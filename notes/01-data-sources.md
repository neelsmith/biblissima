# Biblissima data sources: findings

Status: from documentation only (2026-11-08). NOTHING here has been verified against live
endpoints yet. Items marked UNVERIFIED must be checked before code depends on them.

## Correction to earlier assumptions
An initial web search turned up a 2015 deck describing a CubicWeb / CIDOC-CRM / FRBRoo model
(`bibma:Manuscript`, `carries_text`, `has_digital_surrogate`, `sc:Manifest`). That is the OLD
platform. Current docs (doc.biblissima.fr/api, last updated 2024-05-21, Licence Ouverte 2.0)
describe a Wikibase-based reference repository. Treat the old class and property names as
historical only.

## Current services (doc.biblissima.fr/api/)
| Service | URL | Notes |
|---|---|---|
| Wikibase / MediaWiki API | https://data.biblissima.fr/w/api.php | Standard Wikibase actions; sandbox at data.biblissima.fr/w/Spécial:ApiSandbox |
| Linked data (entities) | https://data.biblissima.fr/entity/Q{id} ; https://data.biblissima.fr/w/Spécial:EntityData/Q{id}.{json,rdf,ttl,nt} | Content negotiation also supported (headers not documented) |
| SPARQL | not publicly accessible | Documented as experimental and "pas encore accessible publiquement". Partners can request access: team@biblissima-condorcet.fr. Engine is QLever since April 2026. Example queries: https://data.biblissima.fr/w/Project:SPARQL_examples |
| IIIF Presentation (portal) | https://portail.biblissima.fr/iiif/ | See below |
| Reconciliation | doc.biblissima.fr/api/api-reconciliation/ | OpenRefine, Datasette. Likely not needed |

### Portal IIIF endpoints
- `/iiif/manifest/ark:/43093/{id_biblissima}`: descriptor manifest (IIIF Pres 2.1). Not a per-manuscript manifest.
- `/iiif/manifest?descriptors=...&date=...`: on-demand search manifest (2.1)
- `/iiif/manifest/nkl.{id_nakala}.json`: CIFM epigraphic manifests (3.0)
- `/iiif/collection/ark:/43093/{id_bbma}`: collection of all manifests tied to one entity, e.g. a manuscript with several scans, or a library's digitised books (2.1). Probably the portal-side route from a manuscript to its manifests. UNVERIFIED.

## Access obstacle
data.biblissima.fr serves an Anubis anti-bot (JavaScript proof-of-work) challenge to automated
fetches, and the sandbox that produced these notes could not reach the host (proxy 403). Do
not try to bypass it. Options: ask the team for sanctioned API/SPARQL access or a documented
User-Agent; use a real browser session for exploration; check whether api.php is exempt
from the challenge; use a Wikibase dump if one is published (ask the team).

## Unknowns to resolve (discovery phase)
1. Property and item IDs (P/Q) for: manuscript (class), holding institution, shelfmark,
   IIIF manifest URL, work, expression, "manuscript contains text/expression", locus/folio.
2. Whether manifests are stored as statements on manuscript items, on separate
   "digital copy" items, or only in the portal.
3. How works vs expressions are modelled and linked (FRBRoo-like?).
4. Whether a SPARQL endpoint can be had (see above); otherwise the library must work
   via the MediaWiki API plus EntityData, which is far slower for bulk work.
5. API rate limits, `User-Agent` policy, maximum batch size (wbgetentities allows
   up to 50 ids per call by default on standard Wikibase).

## Verified (2026-11-08, from user's `notes/bibquery.json`, siteinfo call)
- api.php returns JSON to both a browser and curl from the user's terminal (no challenge on that route).
- MediaWiki 1.43.5; site "Référentiels d'autorité Biblissima"; interface language fr; articlepath /w/$1.
- Extensions include Wikibase (Repository + Client), **CirrusSearch, Elastica, WikibaseCirrusSearch**,
  PropertySuggester. So `haswbstatement:` search is expected to work (still to test).
- Scale: 887,049 pages (~885.7k content pages), 2.7M edits. Pages are not all items, so
  bulk enumeration by plain paging is large; prefer search filters and batched wbgetentities.
- Note: the sandbox/device shells used by Claude get proxy 403s to this host, so live calls must be run
  by the user (or the library tested via saved fixtures) unless that changes.

## Discovered IDs (from keyword searches, 2026-11-08; labels fr; still to confirm on real items)
- P196 "manifeste IIIF": reference URL of the IIIF Presentation JSON-LD document. **Candidate key property for Task 1.**
  - P384 "fonctionnalité IIIF": qualifier on P196 (values e.g. Q407438 IIIF Ranges, Q407436 Content Search, Q407437 Annotations)
  - P189 "URL de la collection IIIF"; P190 "URL de l'API IIIF Change Discovery"
- Q32810 "manuscrit" (class candidate); Q345196 "manuscrits en plusieurs volumes"
- Q282950 "œuvre" (work class candidate). No expression class found by the word "expression" (try "expression de l'œuvre" / "texte").
- Many items are titled "Manuscrit attesté : <title>" (attested manuscripts, i.e. historic catalogue entries); these may
  need excluding or flagging when listing extant manuscripts. To check.
- 430ish properties exist (`samples/properties_pages.json` has only page titles; labels still needed).

## Property IDs confirmed from labels (see 04-property-labels.md for all 365)
- P2 "nature de l'élément" = instance of (item); P7 sous-classe de; P55 concept parent; P52 classe équivalente
- P196 manifeste IIIF (url); P384 fonctionnalité IIIF (qualifier); P189 URL de la collection IIIF; P197 numérisation disponible à l'URL;
  P279 type de numérisation (item); P199 identifiant IIIF-Collections; P210 occurrences de l'entité dans IIIF-Collections
- P195 cote (shelfmark); P194 collection; P201 localisation; P191 bibliothèque numérique
- P169 partie de; P170 comprend (candidates for manuscript <-> part, and possibly manuscript -> text)
- P354 auteur; P355 langue; P359 présent dans l'œuvre; P391 incipit; P403 date de l'œuvre
- P129 identifiant Portail Biblissima; P358 identifiant Comparatio œuvres; P283 identifiant Comparatio manuscrits
- No property literally named "contient"/"texte"/"expression". The manuscript->text link is probably P170 or P359 (inverse). To be determined from real items.
- Q32810 manuscrit and Q345196 have only equivalence statements (P52). Q282950 œuvre has P2=Q304387, P55 (concept parents) and a ThEMA id, so it
  may be a thesaurus concept rather than the class of work items. Do NOT assume haswbstatement:P2=Q282950 selects works.

## Search gotcha
- `haswbstatement:P196` with default namespace returned 0 hits. Items likely live in namespace 120 ("Item:"); properties are in 122.
  Retest with `srnamespace=120`.

## Verified on live data (2026-11-08): search works with srnamespace=120 (items are "Item:Q…")
- `haswbstatement:` works. Counts (items, ns 120): has P196 = 174,678; P2=Q32810 (manuscrit) = 341,828; has P170 = 16,008; has P359 = 1,401.
- Manuscript example Q113537 "Paris. Bibliothèque de l'Arsenal, Ms-5072 réserve": P2=Q32810, P195 cote, P194 collection (Q32813),
  P197 digitisation URL and **P196 manifest URL, both with qualifier P191 (digital library)**, P129 Portail Biblissima id, P198 BnF A&M id, P131 Bibale id,
  P210 IIIF-Collections occurrence. The item has NO statement linking it to texts.
- P170 "comprend" is used (n=176 values) on Bible-chapter style items (Q704411 "[BJ] Psaumes 119"), i.e. work/text part-whole, NOT manuscript->text.
- P359 "présent dans l'œuvre" appears on authority items (e.g. Q290046 person, Q306514 person) pointing to Q287248 / Q306515: person->work, not manuscript->text.
- OPEN RISK: manuscript->text (contents) links may NOT be in this Wikibase at all (they may live in the Portail Biblissima / source databases
  such as Jonas, Pinakes, Bibale). Task 2 feasibility to be confirmed by the combined-count tests.

## Combined counts (2026-11-08, ns 120; samples/counts.tsv)
- manuscripts (P2=Q32810) with manifest P196: 162,779. Items with P196 that are NOT P2=Q32810: 11,899 (class to be identified).
- Manuscripts with P170 / P169 / P359: 0 each. With P354 auteur: 1. So none of these link manuscripts to texts.
- P354 auteur on 6,053 items; P391 incipit on 80 items.
- Work-like items exist: P2=Q282950 (œuvre) = 8,706 items. P2=Q304387 "descripteur" = 24,654 (Q304387 is a thesaurus descriptor,
  so people/concepts are descriptors). Q317414 "unité textuelle", Q460025 "chapitre biblique".
- Portal manuscript pages (portail.biblissima.fr/.../ark:/43093/mdata...) are behind the same Anubis challenge for automated fetches (Claude's WebFetch).

## Samples of works, attested manuscripts, and non-manuscript manifest items (2026-11-08)
- "œuvre" items (P2=Q282950, 8,706): sampled ones are Bible editions/translations (Q457918 [Vg] Vulgate, Q458570 [NRSA] Psaumes, Q457925 [Gig]); they have
  P355 langue, P382 BiblIndex id, P169/P170 part-whole. No manuscript link.
- "Manuscrit attesté" items (3,811 hits): P2=Q32810 but minimal (P129, P250 Esprit des livres id); no manifest, no texts. Exclude from Task 1 naturally (no P196).
- 11,899 non-manuscript items with P196 are class Q113619 (sampled: Boulogne-sur-Mer INC xx, i.e. incunabula likely; label to confirm). These items use P196 =
  api.irht.cnrs.fr manifests and carry P213 ARCA and P139 Initiale ids. Decide whether the library should expose `kind` (manuscript | incunable).
- Candidate counts for other relations: P430 entité correspondante 33,008; P201 localisation 7,217; P398 entité associée 2,492; P290 253; P291 46.
- CONCLUSION SO FAR: the Wikibase référentiel holds manuscripts (identification, shelfmark, collection, manifests, external ids) and works as authorities,
  but sampled manuscript items carry no contents (text) statements. Manuscript->work/expression links are not found here.
- Manuscripts carry external ids that point at catalogues that DO hold contents: P131 Bibale, P140 Jonas, P145 Pinakes, P139 Initiale, P198 BnF Archives et manuscrits,
  P213 ARCA, P283 Comparatio manuscrits. Another possible source: the Portail Biblissima manuscript pages (ark:/43093/mdata...), format unknown (user to inspect).
