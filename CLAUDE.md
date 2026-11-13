

## Overview

`biblissima` is a python library for working with data about manuscripts, the texts contained in them, and images available via IIIF manifests, using the API endpoint from biblissima.fr.


## Functionality

The python library should be packaged for publication on pypi, and should include thorough coverage in unit tests. API docs should be automatically built. It will include marimo notebooks exercising the library.


## Architecture & Directory Structure

- `quarto`, `docs`, `README.md`, `releases.md`, `datareleases.md` and `data-version.txt` are all user-readable content owned by me; Claude should not touch them
- the following data directories have content that should be read-only to Claude: `artifacts`, `audio`, `editions`, `images`
- `notes` is for documentation and notes that Claude writes, includes session summaries so I can reliably pick up working with Claude from different machines
- `src` is for source code



## Testing Guidelines

- Write unit tests for utility functions and integration/component tests for critical UI flows.
- Run relevant tests before proposing significant refactors.