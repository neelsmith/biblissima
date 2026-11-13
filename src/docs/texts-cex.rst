The ``texts.cex`` file
======================

``biblissima texts`` writes ``data/texts.cex``: a UTF-8, pipe-delimited file
that links Biblissima works to CTS (Canonical Text Services) work URNs.

Columns
-------

``biblissima``
    The portal's permanent identifier for the work (``ark:/43093/oedata...``).
``urn``
    The CTS URN of the work, *without* a version and with an empty passage
    component, so it has five colon-separated parts and ends in a colon:
    ``urn:cts:greekLit:tlg0363.tlg001:``.
``group``
    Name of the CTS text group, taken from the CTS catalogue (English if the
    catalogue has it, otherwise Latin), for example ``Claudius Ptolemaeus``.
``work``
    Name of the CTS work, with the same preference, for example
    ``Syntaxis mathematica``.

How matches are made
--------------------

Biblissima holds no CTS identifiers, so matching has two steps.

1. *Author.* A work's authors are the people credited as "Auteur du texte"
   on its texts. A person linked to Wikidata is mapped to a CTS text group
   through the TLG (``P3576``) or PHI Latin (``P6941``) author number that
   Wikidata records for them.
2. *Title.* Inside that group, the work's titles are compared with the CTS
   work titles after folding case, accents and punctuation.

Only matches at or above ``--threshold`` (default 0.85) go to ``texts.cex``.
Weaker or ambiguous matches are written to a separate review file
(``data/texts_review.cex``) with their score and Biblissima label, and are not
part of ``texts.cex``. Works without a Wikidata-linked author in a CTS group
are not matched, so most medieval and vernacular works have no row.

Inputs
------

* the CTS catalogue: ``__cts__.xml`` files from the Perseus and Open Greek and
  Latin repositories (``--cts``);
* a saved Wikidata SPARQL result with TLG and PHI author numbers
  (``--wikidata``), see :mod:`biblissima.wikidata`.
