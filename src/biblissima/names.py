"""Alternative names for text groups and works (``groupnames.cex``, ``worknames.cex``).

Biblissima keeps several name forms for a person (``Person preferred_form`` and
``other_forms``) and for a work (``Work displayed_title``, ``preferred_form`` and
``other_forms``), each a ``Designation`` with a title. This module collects
them for the works listed in ``texts.cex``:

* a work's names go with the work's CTS URN;
* a person's names go with the CTS *group* URN of the works they wrote, but only
  when Wikidata maps that person to the group's TLG/PHI number, so that
  pseudonymous or wrongly attributed authors do not leak in.

Names that merely repeat the CTS name already in ``texts.cex`` are left out.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator

from .client import EmptyResultError, PortalClient
from .export import DELIMITER, write_cex
from .rql import iter_rows
from .texts import BiblissimaWork, fold

GROUP_HEADER = ("urn", "name")
WORK_HEADER = ("urn", "name")

_TRAILING_DATES = re.compile(r"\s*\([^()]*\d[^()]*\)\s*$")
_GLUED = re.compile(r"\)[^\s,;)]")
_AUTHOR_PREFIX = re.compile(r"^[^.]*?,\s*(?:active|fl\.?|ca\.?|b\.|d\.)[^.]*\.\s+", re.I)
_DATE_TAIL = re.compile(
    r"[,;\s-]*(?:\(?\s*(?:fl\.?|active)\s*)?(?:ca\.\s*)?\d{1,4}\??\s*"
    r"(?:-\s*(?:ca\.\s*)?\d{1,4}\??)?\s*(?:av\. J\.-C\.|BC|AD)?\)?\s*$",
    re.I,
)
_CENTURY_TAIL = re.compile(r",?\s*\d+(?:st|nd|rd|th)\s+cent(?:ury|\.)?\s*$", re.I)
_TRANSLATOR = re.compile(r"\s*\((?:trad|transl?)\.[^()]*\)\s*$", re.I)
MAX_NAME_LENGTH = 150


def clean_name(raw: str | None) -> str:
    """Tidy one name form; return ``""`` for forms that should be skipped.

    Unicode is composed (NFC), whitespace collapsed and a trailing life-dates
    parenthesis (``(0100?-0170?)``) removed. A leading author statement such as
    ``Ptolemy, active 2nd century. Almagest`` is cut down to the title. Forms
    where several names were run together (``... (dates)Other name``) are
    skipped.
    """
    if not raw:
        return ""
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", raw)).strip()
    if _GLUED.search(text):
        return ""
    text = _AUTHOR_PREFIX.sub("", text)
    text = _TRAILING_DATES.sub("", text).strip()
    if not text or len(text) > MAX_NAME_LENGTH or "|" in text:
        return ""
    return text


def clean_person_name(raw: str | None) -> str:
    """:func:`clean_name` plus removal of dates left after the name.

    Handles forms such as ``Ptolemaeus, Claudius, 100-178``,
    ``Claudius Ptolemaeus - ca. 100 - ca. 175`` and ``Ptolemy, 2nd cent.``.
    A form with no letters (``168``) is skipped.
    """
    text = clean_name(raw)
    text = _CENTURY_TAIL.sub("", text)
    text = _DATE_TAIL.sub("", text).strip(" ,;-")
    return text if re.search(r"[^\W\d_]", text) else ""


def clean_work_name(raw: str | None) -> str:
    """:func:`clean_name` for titles.

    A trailing translator note ``(trad. ...)`` is removed. Some forms are all
    lowercase and start with the author (``théocrite, poèmes``); those lose the
    author part.
    """
    text = _TRANSLATOR.sub("", clean_name(raw)).strip()
    if text and text == text.lower() and ", " in text:
        text = text.split(", ", 1)[1].strip()
    return text


def group_of(urn: str) -> str:
    """Return the group URN of a work URN (``urn:cts:ns:grp.work:`` -> ``urn:cts:ns:grp:``)."""
    parts = urn.split(":")
    return f"urn:cts:{parts[2]}:{parts[3].split('.')[0]}:"


def load_texts(path: Path | str) -> dict[str, tuple[str, str, str]]:
    """Read ``texts.cex`` as ``{work ark: (urn, group name, work name)}``."""
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return {
            r["biblissima"]: (r["urn"], r["group"], r["work"])
            for r in csv.DictReader(fh, delimiter=DELIMITER)
        }


def fetch_person_qids(client: PortalClient, page_size: int = 2000) -> dict[int, str]:
    """``{person eid: Wikidata QID}`` for persons linked to Wikidata."""
    out: dict[int, str] = {}
    for eid, uri in iter_rows(
        client,
        "P,U",
        'P is Person, P same_as E, E uri U, E uri LIKE "%wikidata.org/entity/Q%"',
        order_by="P,U",
        page_size=page_size,
    ):
        m = re.search(r"wikidata\.org/entity/(Q\d+)", uri or "")
        if m:
            out.setdefault(eid, m.group(1))
    return out


def fetch_work_authors(client: PortalClient, page_size: int = 2000) -> dict[int, set[int]]:
    """``{work eid: {person eids}}`` from "Auteur du texte" contributions."""
    out: dict[int, set[int]] = {}
    for work_eid, person_eid in iter_rows(
        client,
        "W,P",
        'T work W, K book T, K contributor P, K role R, R name "Auteur du texte", P is Person',
        order_by="W,P",
        page_size=page_size,
        distinct=True,
    ):
        out.setdefault(work_eid, set()).add(person_eid)
    return out


def fetch_person_forms(client: PortalClient, page_size: int = 5000) -> dict[int, list[str]]:
    """``{person eid: [name forms]}`` from preferred and other forms."""
    out: dict[int, list[str]] = {}
    for relation in ("preferred_form", "other_forms"):
        try:
            for eid, title in iter_rows(
                client,
                "P,DT",
                f"P is Person, P {relation} D, D title DT",
                order_by="P,DT",
                page_size=page_size,
            ):
                if title:
                    out.setdefault(eid, []).append(title)
        except EmptyResultError:
            pass
    return out


def _unique_names(
    names: Iterable[str], exclude: Iterable[str], clean=clean_name
) -> Iterator[str]:
    seen = {fold(e) for e in exclude}
    for raw in names:
        name = clean(raw)
        key = fold(name)
        if name and key and key not in seen:
            seen.add(key)
            yield name


def build_work_names(
    works: dict[int, BiblissimaWork], texts: dict[str, tuple[str, str, str]]
) -> list[tuple[str, str]]:
    """Sorted unique ``(work URN, name)`` rows."""
    rows: set[tuple[str, str]] = set()
    for work in works.values():
        if work.ark not in texts:
            continue
        urn, _group, cts_name = texts[work.ark]
        for name in _unique_names(work.all_forms(), [cts_name], clean_work_name):
            rows.add((urn, name))
    return sorted(rows)


def build_group_names(
    works: dict[int, BiblissimaWork],
    texts: dict[str, tuple[str, str, str]],
    work_authors: dict[int, set[int]],
    person_qids: dict[int, str],
    person_forms: dict[int, list[str]],
    group_urns: dict[str, list[str]],
) -> list[tuple[str, str]]:
    """Sorted unique ``(group URN, name)`` rows."""
    group_names: dict[str, set[str]] = {}
    persons: dict[str, set[int]] = {}
    for eid, work in works.items():
        if work.ark not in texts:
            continue
        urn, cts_group, _w = texts[work.ark]
        group = group_of(urn)
        group_names.setdefault(group, set()).add(cts_group)
        for person in work_authors.get(eid, ()):
            qid = person_qids.get(person)
            if qid and group in group_urns.get(qid, ()):
                persons.setdefault(group, set()).add(person)
    rows: set[tuple[str, str]] = set()
    for group, people in persons.items():
        forms = [f for p in sorted(people) for f in person_forms.get(p, ())]
        for name in _unique_names(forms, group_names[group], clean_person_name):
            rows.add((group, name))
    return sorted(rows)


def write_names_cex(rows: Iterable[tuple[str, str]], path: Path | str) -> int:
    """Write a two-column ``urn|name`` file; return the row count."""
    return write_cex(path, GROUP_HEADER, rows)
