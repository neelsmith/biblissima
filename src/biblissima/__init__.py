"""Work with data from the Biblissima portal.

Biblissima aggregates data about manuscripts, the texts they contain and
their IIIF manifests. This package reads that data from the public portal
(``portail.biblissima.fr``) and writes it to simple delimited files.
"""

__version__ = "0.1.0"

from .client import (  # noqa: E402
    BiblissimaError,
    EmptyResultError,
    InvalidResponse,
    PortalClient,
    RequestFailed,
    Throttle,
    WikibaseClient,
)
from .export import HEADER, write_mss_cex  # noqa: E402
from .harvest import build_mss_records  # noqa: E402
from .manifests import ManifestRecord, iter_manifest_records  # noqa: E402
from .rights import Library, RightsResolver  # noqa: E402

__all__ = [
    "BiblissimaError",
    "EmptyResultError",
    "HEADER",
    "InvalidResponse",
    "Library",
    "ManifestRecord",
    "PortalClient",
    "RequestFailed",
    "RightsResolver",
    "Throttle",
    "WikibaseClient",
    "build_mss_records",
    "iter_manifest_records",
    "write_mss_cex",
]
