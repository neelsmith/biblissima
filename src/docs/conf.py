"""Sphinx configuration for the biblissima API docs.

Build from the repository root with:
    uv run --group docs sphinx-build -b html src/docs src/docs/_build/html
"""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

from biblissima import __version__  # noqa: E402

project = "biblissima"
author = "biblissima contributors"
release = __version__

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
autosummary_generate = True
autodoc_member_order = "bysource"
html_theme = "furo"
exclude_patterns = ["_build"]
