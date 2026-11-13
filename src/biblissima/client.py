"""HTTP client for the Biblissima portal's RQL endpoint.

The portal is a CubicWeb application. Its ``/view`` URL accepts an RQL
query (``rql=``) and a view name (``vid=``); the ``jsonexport`` view returns
rows as JSON arrays. Two behaviours matter in practice:

* an invalid RQL query returns HTTP 200 with an empty list, not an error;
* very large responses can arrive truncated.

The client therefore refuses empty results unless the caller says an empty
list is a legitimate answer, validates that the body is JSON (retrying if it
is not), throttles requests, and can cache responses on disk.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

import requests

from . import __version__

DEFAULT_BASE_URL = "https://portail.biblissima.fr/en"
DEFAULT_USER_AGENT = f"biblissima-python/{__version__} (research client)"
DEFAULT_WIKIBASE_URL = "https://data.biblissima.fr/w/api.php"
SENTINEL_QUERY = "Any COUNT(X) WHERE X is Manuscript"


class BiblissimaError(Exception):
    """Base class for errors raised by this package."""


class RequestFailed(BiblissimaError):
    """The server could not be reached or kept returning errors."""


class InvalidResponse(BiblissimaError):
    """The server answered, but the body was not usable JSON rows."""


class EmptyResultError(BiblissimaError):
    """An RQL query returned no rows where rows were expected.

    The portal answers invalid queries with an empty list, so an unexpected
    empty result most often means a syntax or schema problem.
    """


class Throttle:
    """Enforce a minimum interval between requests.

    Share one instance between clients so that their *combined* request rate
    stays polite.
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last: Optional[float] = None

    def wait(self) -> None:
        if self._last is not None:
            wait = self.min_interval - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        self._last = self._clock()


class HttpClient:
    """Shared behaviour: throttling, retries, JSON validation, disk cache.

    :param base_url: server URL.
    :param user_agent: sent with every request. Include a way to contact you.
    :param min_interval: minimum seconds between two requests (ignored if
        ``throttle`` is given).
    :param timeout: per-request timeout in seconds.
    :param max_retries: retries after a failed attempt (so ``max_retries + 1`` attempts).
    :param backoff: base of the exponential wait between retries.
    :param cache_dir: if set, successful responses are stored here and reused.
    :param session: object with a ``get`` method like :class:`requests.Session`.
    :param throttle: a shared :class:`Throttle`.
    """

    default_base_url = DEFAULT_BASE_URL

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        *,
        min_interval: float = 1.0,
        timeout: float = 120.0,
        max_retries: int = 3,
        backoff: float = 2.0,
        cache_dir: Optional[Path | str] = None,
        session: Any = None,
        throttle: Optional[Throttle] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_url = (base_url or self.default_base_url).rstrip("/")
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._session = session if session is not None else requests.Session()
        self._sleep = sleep
        self._throttle = throttle or Throttle(min_interval, sleep, clock)

    def _get_json(self, url: str, params: dict) -> Any:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            if attempt:
                self._sleep(self.backoff**attempt)
            self._throttle.wait()
            try:
                resp = self._session.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
            except requests.RequestException as exc:
                last_error = exc
                continue
            status = resp.status_code
            if status == 429 or status >= 500:
                last_error = RequestFailed(f"HTTP {status} from {url}")
                retry_after = getattr(resp, "headers", {}).get("Retry-After")
                if retry_after:
                    try:
                        self._sleep(min(float(retry_after), 60.0))
                    except ValueError:
                        pass
                continue
            if status != 200:
                raise RequestFailed(f"HTTP {status} from {url}")
            try:
                return resp.json()
            except ValueError as exc:
                last_error = InvalidResponse(f"response was not valid JSON: {exc}")
                continue
        raise RequestFailed(
            f"giving up after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error

    def _cache_path(self, key_text: str) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        key = hashlib.sha256(key_text.encode("utf-8")).hexdigest()
        return self.cache_dir / key[:2] / f"{key}.json"

    def _cache_read(self, key_text: str) -> Any:
        path = self._cache_path(key_text)
        if path is None or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _cache_write(self, key_text: str, data: Any) -> None:
        path = self._cache_path(key_text)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


class PortalClient(HttpClient):
    """Polite client for the portal's RQL endpoint (see module docs)."""

    default_base_url = DEFAULT_BASE_URL

    def rql(
        self, query: str, vid: str = "jsonexport", *, allow_empty: bool = False
    ) -> list:
        """Run an RQL query and return the decoded JSON rows.

        :param allow_empty: if false (default), an empty result raises
            :class:`EmptyResultError`.
        """
        key_text = f"{vid}\n{query}"
        cached = self._cache_read(key_text)
        if cached is not None:
            return cached
        data = self._get_json(f"{self.base_url}/view", {"rql": query, "vid": vid})
        if not isinstance(data, list):
            raise InvalidResponse(
                f"expected a JSON list, got {type(data).__name__}: {query!r}"
            )
        if not data and not allow_empty:
            raise EmptyResultError(
                "RQL query returned no rows (the portal also does this for "
                f"invalid queries): {query!r}"
            )
        self._cache_write(key_text, data)
        return data

    def check_endpoint(self) -> int:
        """Confirm the endpoint works and return the number of manuscripts."""
        rows = self.rql(SENTINEL_QUERY)
        try:
            count = int(rows[0][0])
        except (IndexError, TypeError, ValueError) as exc:
            raise InvalidResponse(f"unexpected sentinel answer: {rows!r}") from exc
        if count <= 0:
            raise InvalidResponse(f"sentinel query reported {count} manuscripts")
        return count


class WikibaseClient(HttpClient):
    """Client for the Biblissima authority Wikibase (``data.biblissima.fr``)."""

    default_base_url = DEFAULT_WIKIBASE_URL

    #: wbgetentities accepts at most 50 ids per request.
    MAX_IDS = 50

    def get_entities(
        self,
        ids: Iterable[str],
        *,
        props: str = "claims",
        languages: Sequence[str] = ("en", "fr"),
    ) -> dict:
        """Fetch entities by id (``Q123``); return ``{id: entity}``.

        Missing entities are left out. At most 50 ids per call.
        """
        ids = list(dict.fromkeys(ids))
        if not ids:
            return {}
        if len(ids) > self.MAX_IDS:
            raise ValueError(f"at most {self.MAX_IDS} ids per request")
        params = {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": props,
            "format": "json",
        }
        if "labels" in props:
            params["languages"] = "|".join(languages)
        key_text = json.dumps(params, sort_keys=True)
        cached = self._cache_read(key_text)
        if cached is None:
            data = self._get_json(self.base_url, params)
            if not isinstance(data, dict) or "entities" not in data:
                detail = data.get("error") if isinstance(data, dict) else data
                raise InvalidResponse(f"unexpected Wikibase answer: {detail!r}")
            cached = data["entities"]
            self._cache_write(key_text, cached)
        return {k: v for k, v in cached.items() if "missing" not in v}
