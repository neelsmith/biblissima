The ``mss.cex`` file
====================

``biblissima mss`` writes ``data/mss.cex``: a UTF-8, pipe-delimited text file
with one row per manuscript IIIF manifest. A manuscript with several
manifests has several rows.

Columns
-------

``biblissima``
    The portal's permanent identifier for the manuscript (an ARK such as
    ``ark:/43093/mdata...``).
``label``
    A readable label for the manuscript (its displayed title).
``manifest``
    URL of the IIIF manifest.
``manifest_license``
    Rights or licence terms for the manifest.
``manifest_credits``
    Source or credit statement for the manifest.

Fields that contain the ``|`` delimiter are wrapped in double quotes, as with
CSV (use a CSV reader with ``delimiter="|"``). Line breaks are replaced by
spaces.

Where rights and credits come from
----------------------------------

Both columns come from Biblissima's own data. Each manifest statement on a
manuscript's Wikibase item names the *digital library* that provides it; that
library item gives an operator, sometimes a licence, and sometimes a
conditions-of-use URL.

``manifest_credits``
    ``Digital library (operator)``, for example
    ``DigitVatLib - Biblioteca Apostolica Vaticana (Vatican. Biblioteca apostolica vaticana)``.
``manifest_license``
    The licence name(s) Biblissima records for that library, followed by its
    conditions-of-use URL when there is one, separated by ``;``.

Rights are stated per digital library, not per manifest, and only as far as
Biblissima records them: many libraries have no licence recorded, and those
rows have an empty ``manifest_license``. Rows whose manuscript has no
Wikibase item, or whose manifest matches no digital library, have both
columns empty. Run with ``--no-rights`` to skip the lookups entirely.

This is not the licence in the manifest file itself, which may differ.
