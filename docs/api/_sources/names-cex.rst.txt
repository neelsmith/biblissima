groupnames.cex and worknames.cex
================================

Both files are pipe-delimited with the header ``urn|name``.

``groupnames.cex``
   ``urn`` is a group-level CTS URN (``urn:cts:greekLit:tlg0363:``); ``name`` is
   an alternative name for the group, taken from the name forms Biblissima keeps
   for the author. A person's names are used only when Wikidata maps that person
   to the group's TLG/PHI number. Life dates in parentheses are removed.
``worknames.cex``
   ``urn`` is a work-level CTS URN (``urn:cts:greekLit:tlg0363.tlg001:``); ``name``
   is an alternative title from the work's title, preferred form and other forms.

Names that only repeat the CTS name in ``texts.cex`` are omitted. Build both with
``uv run biblissima names --cache-dir .cache/biblissima``.
