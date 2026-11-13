"""Rights and credits for IIIF manifests, from Biblissima's own data.

Each manifest statement (property ``P196``) on a manuscript's Wikibase item
carries a qualifier ``P191`` naming the *digital library* that provides it.
That library is itself an item, with an operator (``P200``), optionally a
licence (``P187``) and a conditions-of-use URL (``P366``). This module follows
that chain:

    manuscript item --P196[P191]--> digital library --P200/P187/P366--> text

Rights are therefore stated per digital library, not per manifest, and only as
completely as Biblissima records them: many libraries have no licence there,
and those manifests get an empty ``manifest_license``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .client import WikibaseClient

MANIFEST = "P196"
DIGITAL_LIBRARY = "P191"
OPERATOR = "P200"
LICENCE = "P187"
CONDITIONS_URL = "P366"


# -- reading Wikibase JSON -------------------------------------------------


def label_of(entity: dict, qid: str = "") -> str:
    """Best label of an entity: English, then French, then any, then ``qid``."""
    labels = entity.get("labels") or {}
    for lang in ("en", "fr"):
        if lang in labels:
            return labels[lang]["value"]
    for value in labels.values():
        return value["value"]
    return qid


def claims(entity: dict, prop: str) -> list[dict]:
    """Non-deprecated claims of ``prop``."""
    return [
        c
        for c in (entity.get("claims") or {}).get(prop, [])
        if c.get("rank") != "deprecated"
    ]


def snak_value(snak: dict) -> Any:
    """The value of a snak: an item id, or the raw value; ``None`` if absent."""
    if snak.get("snaktype") != "value":
        return None
    value = snak["datavalue"]["value"]
    if isinstance(value, dict) and "id" in value:
        return value["id"]
    return value


def item_ids(entity: dict, prop: str) -> list[str]:
    ids = []
    for c in claims(entity, prop):
        value = snak_value(c["mainsnak"])
        if isinstance(value, str) and value not in ids:
            ids.append(value)
    return ids


def string_values(entity: dict, prop: str) -> list[str]:
    return [
        v
        for c in claims(entity, prop)
        if isinstance(v := snak_value(c["mainsnak"]), str)
    ]


# -- digital libraries ------------------------------------------------------


@dataclass(frozen=True)
class Library:
    """A digital library as Biblissima describes it."""

    qid: str
    label: str
    operators: tuple[str, ...] = ()
    licenses: tuple[str, ...] = ()
    conditions_url: str = ""

    @property
    def credits(self) -> str:
        """``"Library (operator / operator)"``, or just the library name."""
        ops = " / ".join(self.operators)
        if ops and self.label:
            return f"{self.label} ({ops})"
        return self.label or ops

    @property
    def license(self) -> str:
        """Licence names followed by the conditions-of-use URL, ``"; "``-joined."""
        return "; ".join(x for x in (*self.licenses, self.conditions_url) if x)


@dataclass
class RightsStats:
    """Counters describing how well rights could be resolved."""

    records: int = 0
    no_qid: int = 0
    no_library: int = 0
    with_license: int = 0
    libraries: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"{self.records} records; {self.no_qid} without a Wikibase item, "
            f"{self.no_library} whose manifest matched no digital library, "
            f"{self.with_license} with a licence or conditions URL"
        )


class RightsResolver:
    """Resolve ``(manuscript item, manifest URL)`` to license and credits strings."""

    def __init__(self, wikibase: WikibaseClient) -> None:
        self._wb = wikibase
        # qid -> {manifest url -> [library qids]}
        self._manifest_libs: dict[str, dict[str, list[str]]] = {}
        self._libraries: dict[str, Library] = {}
        self._labels: dict[str, str] = {}

    # -- fetching -----------------------------------------------------

    def _fetch(self, ids: Iterable[str], props: str) -> dict:
        ids = list(dict.fromkeys(ids))
        out: dict = {}
        for i in range(0, len(ids), self._wb.MAX_IDS):
            out.update(self._wb.get_entities(ids[i : i + self._wb.MAX_IDS], props=props))
        return out

    def prefetch(self, qids: Iterable[str]) -> None:
        """Load manifest statements for manuscript items not seen yet."""
        todo = [q for q in dict.fromkeys(qids) if q and q not in self._manifest_libs]
        entities = self._fetch(todo, "claims")
        for q in todo:
            by_url: dict[str, list[str]] = {}
            for c in claims(entities.get(q, {}), MANIFEST):
                url = snak_value(c["mainsnak"])
                if not isinstance(url, str):
                    continue
                libs = by_url.setdefault(url.strip(), [])
                for qual in c.get("qualifiers", {}).get(DIGITAL_LIBRARY, []):
                    lib = snak_value(qual)
                    if isinstance(lib, str) and lib not in libs:
                        libs.append(lib)
            self._manifest_libs[q] = by_url
        self._load_libraries(
            lib for by_url in self._manifest_libs.values() for libs in by_url.values() for lib in libs
        )

    def _load_libraries(self, qids: Iterable[str]) -> None:
        new = [q for q in dict.fromkeys(qids) if q not in self._libraries]
        if not new:
            return
        entities = self._fetch(new, "labels|claims")
        needed: list[str] = []
        for q in new:
            ent = entities.get(q, {})
            needed += item_ids(ent, OPERATOR) + item_ids(ent, LICENCE)
        unknown = [q for q in dict.fromkeys(needed) if q not in self._labels]
        for q, ent in self._fetch(unknown, "labels").items():
            self._labels[q] = label_of(ent, q)
        for q in new:
            ent = entities.get(q, {})
            self._libraries[q] = Library(
                qid=q,
                label=label_of(ent, q),
                operators=tuple(self._labels.get(o, o) for o in item_ids(ent, OPERATOR)),
                licenses=tuple(self._labels.get(x, x) for x in item_ids(ent, LICENCE)),
                conditions_url=(string_values(ent, CONDITIONS_URL) or [""])[0],
            )

    # -- lookup -------------------------------------------------------

    def libraries_for(self, qid: str, manifest_url: str) -> list[Library]:
        """Digital libraries recorded for this manifest of this manuscript."""
        libs = self._manifest_libs.get(qid, {}).get(manifest_url.strip(), [])
        return [self._libraries[q] for q in libs if q in self._libraries]

    def rights_for(self, qid: str, manifest_url: str) -> tuple[str, str]:
        """Return ``(license, credits)``; empty strings when unknown."""
        libs = self.libraries_for(qid, manifest_url)
        licence = "; ".join(dict.fromkeys(x for lib in libs if (x := lib.license)))
        credits = "; ".join(dict.fromkeys(x for lib in libs if (x := lib.credits)))
        return licence, credits
