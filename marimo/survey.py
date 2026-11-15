import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import io
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import polars as pl

    from biblissima.release import read_blocks

    return Path, alt, io, mo, pl, read_blocks


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Survey of the Biblissima data release

    Frequencies of manuscript collections, text groups, and
    group / work pairs, read from `datareleases/current.cex`.
    """)
    return


@app.cell(hide_code=True)
def _(mo, mss, texts, version):
    mo.md(f"""
    Release **{version}**: {mss.height:,} manifest rows for
    {mss["biblissima"].n_unique():,} manuscripts, and {texts.height:,} texts.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Manuscripts
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    top_n = mo.ui.slider(10, 100, value=30, step=5, label="Bars to show")
    top_n
    return (top_n,)


@app.cell(hide_code=True)
def _(frequency_chart, mo, mss, pl, top_n):
    # One row per manuscript (a manuscript with several manifests has several rows).
    _manuscripts = mss.unique(subset="biblissima").with_columns(
        pl.col("collection").fill_null("(none recorded)")
    )
    mo.vstack(
        [
            mo.md("## Collections holding manuscripts"),
            frequency_chart(
                _manuscripts, "collection", "Manuscripts per collection", top_n.value
            ),
        ]
    )
    return


@app.cell
def _(mss):
    mss
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Texts
    """)
    return


@app.cell(hide_code=True)
def _(frequency_chart, mo, texts, top_n):
    mo.vstack(
        [
            mo.md("## Text groups"),
            frequency_chart(texts, "group", "Works per text group", top_n.value),
        ]
    )
    return


@app.cell(hide_code=True)
def _(frequency_chart, mo, pl, texts, top_n):
    _pairs = texts.with_columns(
        (pl.col("group") + " - " + pl.col("work")).alias("group_work")
    )
    mo.vstack(
        [
            mo.md("## Text group - work"),
            frequency_chart(_pairs, "group_work", "Rows per group - work", top_n.value),
        ]
    )
    return


@app.cell
def _(texts):
    texts
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


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Load dataframes
    """)
    return


@app.cell
def _(Path, mo, read_blocks):
    _here = mo.notebook_dir() or Path.cwd()
    release_path = next(
        (
            p
            for p in (
                _here / ".." / "datareleases" / "current.cex",
                Path.cwd() / "datareleases" / "current.cex",
            )
            if p.is_file()
        ),
        None,
    )
    mo.stop(
        release_path is None,
        mo.md(
            "**`datareleases/current.cex` not found.** Copy the latest release "
            "there, e.g. `cp datareleases/2026a.cex datareleases/current.cex`."
        ),
    )
    blocks = read_blocks(release_path)
    version = blocks["version"][0]
    return blocks, version


@app.cell
def _(blocks, io, pl):
    def block_frame(name):
        """One release block as a polars frame of strings (header = first line)."""
        text = "\n".join(blocks[name])
        return pl.read_csv(
            io.StringIO(text),
            separator="|",
            quote_char='"',
            infer_schema_length=0,  # keep every column as text
        )

    mss = block_frame("mss")
    texts = block_frame("texts")
    return mss, texts


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Plot results
    """)
    return


@app.cell
def _(alt, pl):
    def frequency_chart(frame, column, title, top_n):
        """Horizontal bar chart of the ``top_n`` most frequent values of a column."""
        counts = (
            frame.group_by(column)
            .agg(pl.len().alias("n"))
            .sort(["n", column], descending=[True, False])
        )
        shown = counts.head(top_n)
        return (
            alt.Chart(alt.Data(values=shown.to_dicts()))
            .mark_bar()
            .encode(
                x=alt.X("n:Q", title="count"),
                y=alt.Y(f"{column}:N", sort="-x", title=None),
                tooltip=[alt.Tooltip(f"{column}:N"), alt.Tooltip("n:Q")],
            )
            .properties(
                title=f"{title} (top {shown.height} of {counts.height:,} values)",
                width=600,
                height=max(60, 18 * shown.height),
            )
        )

    return (frequency_chart,)


if __name__ == "__main__":
    app.run()
