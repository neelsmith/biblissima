import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Browse illustrated manuscripts by collection

    Choose a collection (a library or archive), then a work or "All", to list
    the manuscripts with IIIF manifests that hold it. Each manifest links to
    the IIIF viewer.
    """)
    return


@app.cell(hide_code=True)
def _(collection, mo, workchooser):
    mo.hstack([collection, workchooser], justify="center")
    return


@app.cell(hide_code=True)
def _(
    collection,
    entries_for_collection,
    mo,
    mss,
    render_manuscripts_html,
    textindex,
    texts,
    works,
):
    mo.stop(collection.value is None)
    _selection = works.value[collection.value]
    mo.stop(_selection is None, mo.md("*Choose a work, or All.*"))
    _entries = entries_for_collection(
        collection.value, _selection, textindex, texts, mss
    )
    mo.stop(
        not _entries,
        mo.md("No manuscripts with IIIF manifests are recorded for this choice."),
    )
    mo.vstack(
        [
            mo.md(
                f"### {len(_entries)} manuscript{'' if len(_entries) == 1 else 's'} "
                f"in {collection.value}"
            ),
            mo.Html(render_manuscripts_html(_entries)),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html("<br/><br/><br/><br/><br/><br/><br/><br/><br/>")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Implementation
    """)
    return


@app.cell
def _():
    from pathlib import Path

    from biblissima.browse import (
        collection_options,
        collection_work_options,
        entries_for_collection,
        manuscript_collections,
        render_manuscripts_html,
    )
    from biblissima.release import parse_block, read_blocks

    return (
        Path,
        collection_options,
        collection_work_options,
        entries_for_collection,
        manuscript_collections,
        parse_block,
        read_blocks,
        render_manuscripts_html,
    )


@app.cell
def _(mo):
    mo.md("""
    ## Load data
    """)
    return


@app.cell
def _(Path, manuscript_collections, mo, parse_block, read_blocks):
    _here = mo.notebook_dir() or Path.cwd()
    _candidates = [
        _here / ".." / "datareleases" / "current.cex",
        Path.cwd() / "datareleases" / "current.cex",
        _here / ".." / "data" / "current.cex",
        Path.cwd() / "data" / "current.cex",
    ]
    release_path = next((p for p in _candidates if p.is_file()), None)
    mo.stop(
        release_path is None,
        mo.md(
            "**`datareleases/current.cex` not found.** Copy the latest release "
            "there, e.g. `cp datareleases/2026a.cex datareleases/current.cex`."
        ),
    )
    _blocks = read_blocks(release_path)
    version = _blocks["version"][0]
    texts = parse_block(_blocks["texts"])
    textindex = parse_block(_blocks["textindex"])
    mss = parse_block(_blocks["mss"])
    holders = manuscript_collections(mss)
    return holders, mss, textindex, texts, version


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI
    """)
    return


@app.cell
def _(collection_options, holders, mo, textindex, version):
    collection = mo.ui.dropdown(
        options=collection_options(textindex, holders),
        label=f"Collection (release {version})",
        full_width=True,
    )

    return (collection,)


@app.cell
def _(
    collection_options,
    collection_work_options,
    holders,
    mo,
    textindex,
    texts,
):
    # One work menu per collection, all built once. Choosing a collection only
    # decides which of these menus is shown, so no menu is ever rebuilt
    # (a menu rebuilt by a dependent cell showed stale options in the browser).
    works = mo.ui.dictionary(
        {
            name: mo.ui.dropdown(
                options=collection_work_options(name, textindex, texts, holders),
                label=f"Works in {name}",
                full_width=True,
            )
            for name in collection_options(textindex, holders).values()
        }
    )
    return (works,)


@app.cell
def _(collection, mo):
    mo.stop(collection.value is None, mo.md("*Choose a collection.*"))
    #works[collection.value]
    return


@app.cell
def _(collection, works):
    workchooser = None
    if collection.value:
        workchooser = works[collection.value]
    return (workchooser,)


if __name__ == "__main__":
    app.run()
