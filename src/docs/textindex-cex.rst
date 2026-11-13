textindex.cex
=============

``data/textindex.cex`` is pipe-delimited with the header ``mss|text|location``.

``mss``
   Biblissima identifier of a manuscript; always present in ``mss.cex``.
``text``
   CTS work URN; always present in ``texts.cex``.
``location``
   Folio range where the text occurs, as recorded by Biblissima's
   ``minmax_folios`` field and tidied (leading zeros and a trailing ``*`` removed).
   Empty when Biblissima does not say. Folio labels are strings (``63bisr``). Forms such as ``32r-v`` become ``32r-32v``; a ``f.`` prefix is dropped.
   Recto/verso is never guessed: ``168-170`` stays ``168-170``.

Build it with ``uv run biblissima textindex --cache-dir .cache/biblissima``.
