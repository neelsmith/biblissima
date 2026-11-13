"""Map Wikidata items to CTS text groups via TLG and PHI author identifiers.

Wikidata records the Thesaurus Linguae Graecae author number (e.g. ``0363``
for Ptolemy) and the PHI Latin Texts author number. Those numbers are the group
part of CTS URNs in the ``greekLit`` (``tlg0363``) and ``latinLit``
(``phi0690``) namespaces.

The mapping is read from a SPARQL JSON result saved beforehand, with variables
``?p`` (the person), ``?tlg`` and ``?phi`` (the numbers); see
:data:`SPARQL_QUERY`. A result whose ``?tlg`` or ``?phi`` values are not plain
digit strings is rejected.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

#: Wikidata properties: P3576 = TLG author ID, P6941 = PHI Latin Texts author ID.
#: (Check numbers on Wikidata itself: other Wikibase sites number properties differently.)
SPARQL_QUERY = (
    "SELECT ?p ?tlg ?phi WHERE { "
    "{ ?p wdt:P3576 ?tlg } UNION { ?p wdt:P6941 ?phi } }"
)

_QID = re.compile(r"/(Q\d+)$")


def load_group_urns(path: Path | str) -> dict[str, list[str]]:
    """Return ``{wikidata qid: [group URNs with trailing colon]}``.

    :raises ValueError: if more than 5% of the author numbers are not plain
        digit strings, which means the wrong Wikidata properties were queried.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, list[str]] = defaultdict(list)
    total = bad = 0
    for row in data["results"]["bindings"]:
        for var in ("tlg", "phi"):
            if var in row:
                total += 1
                if not row[var]["value"].strip().isdigit():
                    bad += 1
    if total and bad / total > 0.05:
        raise ValueError(
            f"{bad} of {total} TLG/PHI values are not plain numbers: "
            "the SPARQL query probably used the wrong Wikidata properties"
        )
    for row in data["results"]["bindings"]:
        m = _QID.search(row["p"]["value"])
        if not m:
            continue
        for var, ns, prefix in (("tlg", "greekLit", "tlg"), ("phi", "latinLit", "phi")):
            if var in row:
                number = row[var]["value"].strip()
                if number.isdigit():
                    urn = f"urn:cts:{ns}:{prefix}{number.zfill(4)}:"
                    if urn not in out[m.group(1)]:
                        out[m.group(1)].append(urn)
    return dict(out)
