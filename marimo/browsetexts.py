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
    # Browse illustrated manuscripts by text

    Choose a text group (an author, for example), then a work, to list the
    manuscripts with IIIF manifests that contain it. Each manifest links to
    the IIIF viewer.
    """)
    return


@app.cell(hide_code=True)
def _(group, mo, workchooser):
    mo.hstack([group ,workchooser], justify="center")
    return


@app.cell(hide_code=True)
def _(
    group,
    manuscripts_for_work,
    mo,
    mss,
    render_manuscripts_html,
    textindex,
    works,
):
    mo.stop(group.value is None)
    _urn = works.value[group.value]
    mo.stop(_urn is None, mo.md("*Choose a work.*"))
    _entries = manuscripts_for_work(_urn, textindex, mss)
    mo.stop(
        not _entries,
        mo.md(f"No manuscripts with IIIF manifests are recorded for `{_urn}`."),
    )
    mo.vstack(
        [
            mo.md(
                f"### {len(_entries)} manuscript{'' if len(_entries) == 1 else 's'} "
                f"containing `{_urn}`"
            ),
            mo.Html(render_manuscripts_html(_entries)),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.Html("<br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Implementation
    """)
    return


@app.cell
def _():


    from biblissima.browse import (
        group_options,
        manuscript_counts,
        manuscripts_for_work,
        render_manuscripts_html,
        work_options,
    )
    from biblissima.release import parse_block, read_blocks
    from pathlib import Path

    return (
        Path,
        group_options,
        manuscript_counts,
        manuscripts_for_work,
        parse_block,
        read_blocks,
        render_manuscripts_html,
        work_options,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Read source data
    """)
    return


@app.cell
def _(Path, manuscript_counts, mo, parse_block, read_blocks):
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
    counts = manuscript_counts(textindex)
    return counts, mss, textindex, texts, version


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## UI
    """)
    return


@app.cell
def _(group_options, mo, texts, version):
    group = mo.ui.dropdown(
        options=group_options(texts),
        label=f"Text group (release {version})",
        full_width=True,
    )

    return (group,)


@app.cell(hide_code=True)
def _(counts, mo, texts, work_options):
    # One work menu per text group, all built once. Choosing a group only
    # decides which of these menus is shown, so no menu is ever rebuilt.
    works = mo.ui.dictionary(
        {
            name: mo.ui.dropdown(
                options=work_options(texts, name, counts),
                label=f"Work in {name}",
                full_width=True,
            )
            for name in sorted({row["group"] for row in texts})
        }
    )
    return (works,)


@app.cell
def _(group, works):
    workchooser = None
    if group.value:
        workchooser = works[group.value]
    return (workchooser,)


if __name__ == "__main__":
    app.run()
