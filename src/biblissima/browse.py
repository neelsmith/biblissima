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

    Each item has the label in bold, then a second line with the collection and
    location, then a button-style link for each manifest.
    """
    esc = html.escape
    items = []
    for e in entries:
        many = len(e["manifests"]) > 1
        links = "".join(
            f'<a href="{esc(viewer_url(m), quote=True)}" target="_blank" '
            f'rel="noopener" style="{_BUTTON_STYLE}">'
            f'View images{f" {i}" if many else ""} &#9656;</a>'
            for i, m in enumerate(e["manifests"], 1)
        )
        details = [esc(e["collection"])] if e["collection"] else []
        if e["locations"]:
            details.append("location: " + esc("; ".join(e["locations"])))
        meta = f"<div>{' &middot; '.join(details)}</div>" if details else ""
        items.append(
            f"<li style=\"margin-bottom:0.8em\"><strong>{esc(e['label'])}</strong>"
            f"{meta}<div>{links}</div></li>"
        )
    return "<ul>" + "".join(items) + "</ul>"
