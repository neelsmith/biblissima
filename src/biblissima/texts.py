"""Match Biblissima works to CTS works and build ``texts.cex``.

There is no Biblissima-to-CTS mapping in the data, so matching is in two steps:

1. *Author.* Each Biblissima work has authors (people credited as "Auteur du
   texte" on its texts). A person linked to Wikidata is mapped to a CTS text
   group through the TLG / PHI author numbers Wikidata records
   (:mod:`biblissima.wikidata`).
2. *Title.* Within that group, the work's titles (French, Latin...) are compared
   with the CTS work titles after folding case, accents and punctuation.

Only matches above ``threshold`` are written to ``texts.cex``; weaker ones go
to a review list.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Iterator, Optional

from .client import EmptyResultError, PortalClient
from .cts import CtsCatalog, CtsWork
from .rql import iter_rows

#: Columns of ``texts.cex``.
HEADER = ("biblissima", "urn", "group", "work")
REVIEW_HEADER = ("biblissima", "urn", "group", "work", "score", "label")

_STOP = {
    "de", "des", "du", "la", "le", "les", "l", "d", "in", "ad", "et", "ab",
    "ex", "cum", "sur", "of", "the", "a",
}  # fmt: skip
_NON_WORD = re.compile(r"[\W_]+")


def fold(text: str) -> str:
    """Fold case, accents and punctuation; drop small function words."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    tokens = [t for t in _NON_WORD.split(plain) if t and t not in _STOP]
    return " ".join(tokens)


def strip_author(displayed_title: str) -> str:
    """``"Homère : Odyssée"`` -> ``"Odyssée"``; titles without an author are unchanged."""
    head, sep, tail = displayed_title.partition(" : ")
    return tail.strip() if sep and tail.strip() else displayed_title.strip()


def title_score(forms: Iterable[str], cts_titles: Iterable[str]) -> float:
    """Best similarity (0-1) between any Biblissima form and any CTS title."""
    best = 0.0
    folded_cts = [f for f in (fold(t) for t in cts_titles) if f]
    for form in forms:
        a = fold(form)
        if not a:
            continue
        for b in folded_cts:
            score = 1.0 if a == b else SequenceMatcher(None, a, b).ratio()
            best = max(best, score)
    return best


@dataclass
class BiblissimaWork:
    ark: str
    title: str
    forms: list[str] = field(default_factory=list)
    author_qids: set[str] = field(default_factory=set)

    def all_forms(self) -> list[str]:
        forms = [strip_author(self.title), *self.forms]
        return list(dict.fromkeys(f for f in forms if f))


@dataclass(frozen=True)
class TextMatch:
    ark: str
    label: str
    urn: str
    group: str
    work: str
    score: float


def match_work(
    work: BiblissimaWork,
    catalog: CtsCatalog,
    group_urns_by_qid: dict[str, list[str]],
) -> list[TextMatch]:
    """Return candidate matches for one work, best first (ties are all returned)."""
    groups = {
        g
        for qid in work.author_qids
        for g in group_urns_by_qid.get(qid, [])
        if g in catalog.groups
    }
    forms = work.all_forms()
    scored: list[tuple[float, CtsWork]] = []
    for g in sorted(groups):
        for cw in catalog.works_in_group(g):
            s = title_score(forms, cw.titles.values())
            if s > 0:
                scored.append((s, cw))
    if not scored:
        return []
    top = max(s for s, _ in scored)
    return [
        TextMatch(
            ark=work.ark,
            label=work.title,
            urn=cw.urn,
            group=catalog.groups[cw.group_urn].name,
            work=cw.title,
            score=round(s, 3),
        )
        for s, cw in sorted(scored, key=lambda x: (-x[0], x[1].urn))
        if s >= top - 1e-9
    ]


def split_matches(
    matches: Iterable[list[TextMatch]], threshold: float, review_threshold: float
) -> tuple[list[TextMatch], list[TextMatch]]:
    """Separate confident matches from ones worth a human look.

    A work whose best score ties between several CTS works is ambiguous and
    goes to review even if the score is high.
    """
    accepted: list[TextMatch] = []
    review: list[TextMatch] = []
    for candidates in matches:
        if not candidates:
            continue
        best = candidates[0].score
        if best >= threshold and len(candidates) == 1:
            accepted.append(candidates[0])
        elif best >= review_threshold:
            review.extend(candidates)
    return accepted, review


# -- reading Biblissima works from the portal ---------------------------------


def _rows(client: PortalClient, select: str, where: str, order: str, **kw) -> Iterator[list]:
    return iter_rows(client, select, where, order_by=order, **kw)


def fetch_works(client: PortalClient, *, page_size: int = 2000) -> dict[int, BiblissimaWork]:
    """All works: ``{eid: BiblissimaWork}`` with title and alternative forms."""
    works: dict[int, BiblissimaWork] = {}
    for eid, ark, title in _rows(
        client, "W,WA,WT", "W is Work, W ark WA, W displayed_title WT", "W", page_size=page_size
    ):
        works[eid] = BiblissimaWork(ark=ark, title=(title or "").strip())
    for relation in ("preferred_form", "other_forms"):
        try:
            for eid, form in _rows(
                client,
                "W,DT",
                f"W is Work, W {relation} D, D title DT",
                "W,DT",
                page_size=page_size,
            ):
                if eid in works and form:
                    works[eid].forms.append(form.strip())
        except EmptyResultError:
            pass  # a relation with no rows at all is not an error here
    return works


def attach_authors(
    client: PortalClient,
    works: dict[int, BiblissimaWork],
    *,
    page_size: int = 2000,
) -> None:
    """Fill ``author_qids`` from "Auteur du texte" contributions and Wikidata links."""
    person_qids: dict[int, str] = {}
    for eid, uri in _rows(
        client,
        "P,U",
        'P is Person, P same_as E, E uri U, E uri LIKE "%wikidata.org/entity/Q%"',
        "P,U",
        page_size=page_size,
    ):
        m = re.search(r"wikidata\.org/entity/(Q\d+)", uri or "")
        if m:
            person_qids.setdefault(eid, m.group(1))
    for work_eid, person_eid in _rows(
        client,
        "W,P",
        'T work W, K book T, K contributor P, K role R, R name "Auteur du texte", P is Person',
        "W,P",
        page_size=page_size,
        distinct=True,
    ):
        qid = person_qids.get(person_eid)
        if qid and work_eid in works:
            works[work_eid].author_qids.add(qid)


def write_texts_cex(matches: Iterable[TextMatch], path) -> int:
    """Write confident matches as ``texts.cex`` (``biblissima|urn|group|work``)."""
    from .export import write_cex

    rows = sorted({(m.ark, m.urn, m.group, m.work) for m in matches})
    return write_cex(path, HEADER, rows)


def write_review_cex(matches: Iterable[TextMatch], path) -> int:
    """Write weaker or ambiguous matches for manual review."""
    from .export import write_cex

    rows = sorted(
        {(m.ark, m.urn, m.group, m.work, f"{m.score:.3f}", m.label) for m in matches}
    )
    return write_cex(path, REVIEW_HEADER, rows)
