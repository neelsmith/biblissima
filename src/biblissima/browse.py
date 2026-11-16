"""Logic behind the browsing notebook: menus and manuscript lists.

Everything works on plain lists of dicts, as returned by
:func:`biblissima.release.parse_block` for the ``#!texts``, ``#!textindex`` and
``#!mss`` blocks of a release file.
"""

from __future__ import annotations

import html
from collections import Counter
from urllib.parse import quote

#: Viewer page; the manifest URL follows ``#manifest=``.
VIEWER = "https://neelsmith.github.io/iiif-cite/iiif-cite.html#manifest="

#: Characters left alone when a manifest URL is put after ``#manifest=``.
_URL_SAFE = ":/?#[]@!$&'()*+,;=%~"


def viewer_url(manifest: str) -> str:
    """Link that opens ``manifest`` in the IIIF viewer.

    The manifest URL is used as it is; only characters that cannot appear in a
    link (spaces, quotes, ``<``, ``>``, non-ASCII) are percent-encoded.
    """
    return VIEWER + quote(manifest.strip(), safe=_URL_SAFE)


#: Base of the portal's manuscript pages; the manuscript's ark follows.
PORTAL = "https://portail.biblissima.fr/"


def portal_url(ark: str) -> str:
    """Link to a manuscript's page on the Biblissima portal."""
    return PORTAL + quote(ark.strip(), safe=_URL_SAFE)


def manuscript_counts(textindex: list[dict[str, str]]) -> dict[str, int]:
    """``{work URN: number of distinct manuscripts}`` from the text index."""
    found: dict[str, set[str]] = {}
    for row in textindex:
        found.setdefault(row["text"], set()).add(row["mss"])
    return {urn: len(arks) for urn, arks in found.items()}


def group_options(texts: list[dict[str, str]]) -> dict[str, str]:
    """Menu of text groups: ``{label: group name}``, alphabetical.

    The label shows how many works the group has.
    """
    counts = Counter(row["group"] for row in texts)
    return {
        f"{name} ({n} work{'' if n == 1 else 's'})": name
        for name, n in sorted(counts.items(), key=lambda kv: kv[0].casefold())
    }


def work_options(
    texts: list[dict[str, str]], group: str, counts: dict[str, int]
) -> dict[str, str]:
    """Menu of the works in a group: ``{label: work URN}``, alphabetical.

    The label shows how many manuscripts contain the work. If two works would
    get the same label, the URN is added to tell them apart.
    """
    rows = sorted(
        (r for r in texts if r["group"] == group),
        key=lambda r: (r["work"].casefold(), r["urn"]),
    )
    options: dict[str, str] = {}
    for row in rows:
        n = counts.get(row["urn"], 0)
        label = f"{row['work']} ({n} MS{'' if n == 1 else 'S'})"
        if label in options:
            label = f"{label} [{row['urn']}]"
        options[label] = row["urn"]
    return options


def manuscripts_for_work(
    urn: str, textindex: list[dict[str, str]], mss: list[dict[str, str]]
) -> list[dict]:
    """Manuscripts containing the work, each with its manifests.

    Returns dicts with ``ark``, ``label``, ``collection``, ``locations`` (list)
    and ``manifests`` (list of URLs), sorted by collection and then label.
    Manuscripts that are not in ``mss`` (and so have no manifest) are skipped.
    """
    locations: dict[str, list[str]] = {}
    for row in textindex:
        if row["text"] != urn:
            continue
        locs = locations.setdefault(row["mss"], [])
        if row["location"] and row["location"] not in locs:
            locs.append(row["location"])
    entries: dict[str, dict] = {}
    for row in mss:
        ark = row["biblissima"]
        if ark not in locations:
            continue
        entry = entries.setdefault(
            ark,
            {
                "ark": ark,
                "label": row["label"],
                "collection": row.get("collection", ""),
                "locations": locations[ark],
                "manifests": [],
            },
        )
        url = row["manifest"].strip()
        if url and url not in entry["manifests"]:
            entry["manifests"].append(url)
    return sorted(
        entries.values(),
        key=lambda e: (e["collection"].casefold(), e["label"].casefold()),
    )


#: Inline style that makes a manifest link look like a button.
_BUTTON_STYLE = (
    "display:inline-block;margin:2px 6px 2px 0;padding:2px 10px;"
    "background:#1a5fb4;color:#fff;border-radius:4px;font-weight:600;"
    "text-decoration:none"
)


def render_manuscripts_html(entries: list[dict]) -> str:
    """An HTML list of manuscripts.

    Each item has the label in bold, then a line with the collection and
    location, then (if the entry has ``works``, a list of ``(name, locations)``)
    one line per work, then button-style links: one to the manuscript's Biblissima
    portal page and one for each manifest.
    """
    esc = html.escape
    items = []
    for e in entries:
        many = len(e["manifests"]) > 1
        portal_link = (
            f'<a href="{esc(portal_url(e["ark"]), quote=True)}" target="_blank" '
            f'rel="noopener" style="{_BUTTON_STYLE}">View Biblissima &#9656;</a>'
        )
        links = "".join(
            f'<a href="{esc(viewer_url(m), quote=True)}" target="_blank" '
            f'rel="noopener" style="{_BUTTON_STYLE}">'
            f'View images{f" {i}" if many else ""} &#9656;</a>'
            for i, m in enumerate(e["manifests"], 1)
        )
        details = [esc(e["collection"])] if e["collection"] else []
        if e.get("locations"):
            details.append("location: " + esc("; ".join(e["locations"])))
        meta = f"<div>{' &middot; '.join(details)}</div>" if details else ""
        for name, locs in e.get("works", ()):
            where = f" &mdash; {esc('; '.join(locs))}" if locs else ""
            meta += f"<div>{esc(name)}{where}</div>"
        items.append(
            f"<li style=\"margin-bottom:0.8em\"><strong>{esc(e['label'])}</strong>"
            f"{meta}<div>{portal_link}{links}</div></li>"
        )
    return "<ul>" + "".join(items) + "</ul>"


# -- browsing by collection ---------------------------------------------------

#: Collection name used for manuscripts whose holder is not recorded.
NO_COLLECTION = "(none recorded)"

#: Menu value meaning "every work in the collection".
ALL = "*all*"


def manuscript_collections(mss: list[dict[str, str]]) -> dict[str, str]:
    """``{manuscript ark: collection}``; a blank collection becomes :data:`NO_COLLECTION`."""
    found: dict[str, str] = {}
    for row in mss:
        found.setdefault(row["biblissima"], row.get("collection", "") or NO_COLLECTION)
    return found


def text_names(texts: list[dict[str, str]]) -> dict[str, str]:
    """``{work URN: "group - work"}``."""
    names: dict[str, str] = {}
    for row in texts:
        names.setdefault(row["urn"], f"{row['group']} - {row['work']}")
    return names


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def collection_options(
    textindex: list[dict[str, str]], holders: dict[str, str]
) -> dict[str, str]:
    """Menu of collections that hold manuscripts with indexed texts.

    ``{label: collection}``, alphabetical; labels show the manuscript count.
    """
    arks: dict[str, set[str]] = {}
    for row in textindex:
        collection = holders.get(row["mss"])
        if collection is not None:
            arks.setdefault(collection, set()).add(row["mss"])
    return {
        f"{name} ({_plural(len(found), 'MS', 'MSS')})": name
        for name, found in sorted(arks.items(), key=lambda kv: kv[0].casefold())
    }


def collection_work_options(
    collection: str,
    textindex: list[dict[str, str]],
    texts: list[dict[str, str]],
    holders: dict[str, str],
) -> dict[str, str]:
    """Menu of the works found in a collection: ``{label: work URN}``.

    The first entry, ``All``, has the value :data:`ALL`. Other labels are
    ``group - work (N MSS)``, alphabetical.
    """
    names = text_names(texts)
    per_work: dict[str, set[str]] = {}
    for row in textindex:
        if holders.get(row["mss"]) == collection:
            per_work.setdefault(row["text"], set()).add(row["mss"])
    all_arks = set().union(*per_work.values()) if per_work else set()
    options = {
        f"All ({_plural(len(per_work), 'work', 'works')} in "
        f"{_plural(len(all_arks), 'manuscript', 'manuscripts')})": ALL
    }
    for urn, found in sorted(
        per_work.items(), key=lambda kv: (names.get(kv[0], kv[0]).casefold(), kv[0])
    ):
        label = f"{names.get(urn, urn)} ({_plural(len(found), 'MS', 'MSS')})"
        if label in options:
            label = f"{label} [{urn}]"
        options[label] = urn
    return options


def entries_for_collection(
    collection: str,
    selection: str,
    textindex: list[dict[str, str]],
    texts: list[dict[str, str]],
    mss: list[dict[str, str]],
) -> list[dict]:
    """Manuscripts of a collection with one work, or with every work (:data:`ALL`).

    Each entry has ``ark``, ``label``, ``manifests`` and an empty ``collection``
    (the collection is already known in this view). For one work it has
    ``locations``; for ``ALL`` it has ``works``, a sorted list of
    ``("group - work", [locations])``. Sorted by label.
    """
    holders = manuscript_collections(mss)
    names = text_names(texts)
    found: dict[str, dict[str, list[str]]] = {}
    for row in textindex:
        ark = row["mss"]
        if holders.get(ark) != collection:
            continue
        if selection != ALL and row["text"] != selection:
            continue
        locs = found.setdefault(ark, {}).setdefault(row["text"], [])
        if row["location"] and row["location"] not in locs:
            locs.append(row["location"])
    entries: dict[str, dict] = {}
    for row in mss:
        ark = row["biblissima"]
        if ark not in found:
            continue
        entry = entries.get(ark)
        if entry is None:
            per_work = found[ark]
            entry = {
                "ark": ark,
                "label": row["label"],
                "collection": "",
                "manifests": [],
            }
            if selection == ALL:
                entry["works"] = sorted(
                    ((names.get(u, u), locs) for u, locs in per_work.items()),
                    key=lambda w: w[0].casefold(),
                )
            else:
                entry["locations"] = per_work[selection]
            entries[ark] = entry
        url = row["manifest"].strip()
        if url and url not in entry["manifests"]:
            entry["manifests"].append(url)
    return sorted(entries.values(), key=lambda e: e["label"].casefold())
