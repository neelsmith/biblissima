"""Shared test helpers: a scripted fake HTTP session and a scripted fake client."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None, bad_json=False):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("truncated")
        return self._payload


class FakeSession:
    """Returns scripted responses in order and records each call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClient:
    """Stands in for PortalClient: answers rql() from a list of pages."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.queries = []
        self.allow_empty_flags = []

    def rql(self, query, vid="jsonexport", *, allow_empty=False):
        self.queries.append(query)
        self.allow_empty_flags.append(allow_empty)
        rows = self.pages.pop(0) if self.pages else []
        if not rows and not allow_empty:
            from biblissima import EmptyResultError

            raise EmptyResultError(query)
        return rows


class FakeWikibase:
    """Stands in for WikibaseClient: serves entities from a dict."""

    MAX_IDS = 50

    def __init__(self, entities):
        self.entities = entities
        self.calls = []

    def get_entities(self, ids, *, props="claims", languages=("en", "fr")):
        ids = list(ids)
        assert len(ids) <= self.MAX_IDS
        self.calls.append((ids, props))
        return {q: self.entities[q] for q in ids if q in self.entities}
