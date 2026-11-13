"""Read the CTS catalogue (``__cts__.xml`` metadata files) of Perseus / OGL repos.

A Canonical Text Services (CTS) URN names a text hierarchically. At the *work*
level it has the form ``urn:cts:<namespace>:<group>.<work>:``, for example
``urn:cts:greekLit:tlg0363.tlg001:``: five colon-separated components, the
last (the passage) empty. The catalogue files omit the trailing colon, so
:func:`work_urn` and :func:`group_urn` add it.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

_NS = "{http://chs.harvard.edu/xmlns/cts}"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_GROUP = re.compile(r"urn:cts:([A-Za-z]+):([A-Za-z0-9]+)")
_WORK = re.compile(r"urn:cts:([A-Za-z]+):([A-Za-z0-9]+)\.([A-Za-z0-9]+)")

#: Order in which names are preferred when several languages exist.
NAME_LANGS = ("eng", "lat", "mul", "grc", "fre")
_LANG_ALIASES = {"en": "eng", "la": "lat", "latl": "lat", "fr": "fre", "el": "grc"}


def group_urn(urn: str) -> str:
    """Return the group URN with its trailing colon: ``urn:cts:greekLit:tlg0363:``."""
    m = _GROUP.fullmatch(urn.strip().rstrip(":").split(".")[0])
    if not m:
        raise ValueError(f"not a CTS group or work URN: {urn!r}")
    return f"urn:cts:{m.group(1)}:{m.group(2)}:"


def work_urn(urn: str) -> str:
    """Return the work URN with its trailing colon: ``urn:cts:greekLit:tlg0363.tlg001:``."""
    m = _WORK.fullmatch(urn.strip().rstrip(":"))
    if not m:
        raise ValueError(f"not a CTS work URN: {urn!r}")
    return f"urn:cts:{m.group(1)}:{m.group(2)}.{m.group(3)}:"


def _lang(code: Optional[str]) -> str:
    code = (code or "?").strip().lower()
    return _LANG_ALIASES.get(code, code)


def pick_name(names: dict[str, str]) -> str:
    """Choose one name: English, then Latin, then other languages in a fixed order."""
    for lang in NAME_LANGS:
        if names.get(lang):
            return names[lang]
    for lang in sorted(names):
        if names[lang]:
            return names[lang]
    return ""


@dataclass
class CtsGroup:
    urn: str  # with trailing colon
    names: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return pick_name(self.names)


@dataclass
class CtsWork:
    urn: str  # with trailing colon
    group_urn: str  # with trailing colon
    titles: dict[str, str] = field(default_factory=dict)

    @property
    def title(self) -> str:
        return pick_name(self.titles)


@dataclass
class CtsCatalog:
    groups: dict[str, CtsGroup] = field(default_factory=dict)
    works: dict[str, CtsWork] = field(default_factory=dict)
    _by_group: Optional[dict[str, list[CtsWork]]] = field(default=None, repr=False)

    def works_in_group(self, group: str) -> list[CtsWork]:
        """Works of a group (URN with trailing colon), in URN order."""
        if self._by_group is None:
            index: dict[str, list[CtsWork]] = {}
            for urn in sorted(self.works):
                work = self.works[urn]
                index.setdefault(work.group_urn, []).append(work)
            self._by_group = index
        return self._by_group.get(group, [])

    def _merge_names(self, target: dict[str, str], new: dict[str, str]) -> None:
        for lang, text in new.items():
            target.setdefault(lang, text)  # first file seen wins per language

    def add_file(self, path: Path) -> None:
        """Add one ``__cts__.xml`` file (a textgroup or a work)."""
        self._by_group = None
        root = ET.parse(path).getroot()
        if root.tag == _NS + "textgroup":
            urn = group_urn(root.attrib["urn"])
            names = {
                _lang(n.get(_XML_LANG)): (n.text or "").strip()
                for n in root.findall(_NS + "groupname")
                if (n.text or "").strip()
            }
            self._merge_names(self.groups.setdefault(urn, CtsGroup(urn)).names, names)
        elif root.tag == _NS + "work":
            urn = work_urn(root.attrib["urn"])
            titles = {
                _lang(n.get(_XML_LANG)): (n.text or "").strip()
                for n in root.findall(_NS + "title")
                if (n.text or "").strip()
            }
            grp = group_urn(root.get("groupUrn") or urn)
            work = self.works.setdefault(urn, CtsWork(urn, grp))
            self._merge_names(work.titles, titles)


def load_catalog(paths: Iterable[Path | str]) -> CtsCatalog:
    """Load every ``__cts__.xml`` below the given directories.

    Files are read in sorted order so the result does not depend on the
    file system. Where several repositories describe the same URN, names are
    merged and the first one seen wins for each language.
    """
    catalog = CtsCatalog()
    for base in paths:
        for path in sorted(Path(base).rglob("__cts__.xml")):
            catalog.add_file(path)
    return catalog
