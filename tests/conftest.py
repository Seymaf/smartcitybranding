"""Test helpers: route connector HTTP calls to canned API responses."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.base import BaseConnector  # noqa: E402
from core.config import CREDENTIAL_NAMES  # noqa: E402


class FakeHTTP:
    """Maps URL substrings to responses; records every call."""

    def __init__(self):
        self.routes = []
        self.calls = []

    def add(self, url_part, response, when=None):
        """`when(params_or_body)` optionally narrows a route (e.g. by mode)."""
        self.routes.append((url_part, response, when))

    def _dispatch(self, method, url, payload):
        self.calls.append((method, url, payload))
        for part, response, when in self.routes:
            if part in url and (when is None or when(payload or {})):
                if isinstance(response, Exception):
                    raise response
                return response(payload) if callable(response) else response
        raise AssertionError(f"unexpected {method} {url} {payload}")


@pytest.fixture
def http(monkeypatch):
    fake = FakeHTTP()
    monkeypatch.setattr(BaseConnector, "get_json", classmethod(lambda cls, url, params=None, headers=None, auth=None: fake._dispatch("GET", url, params)))
    monkeypatch.setattr(BaseConnector, "post_json", classmethod(lambda cls, url, payload, headers=None: fake._dispatch("POST", url, payload)))
    monkeypatch.setattr(BaseConnector, "post_form", classmethod(lambda cls, url, data, headers=None, auth=None: fake._dispatch("POST", url, data)))
    return fake


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch):
    for name in CREDENTIAL_NAMES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def creds(monkeypatch):
    def _set(*names):
        for name in names:
            monkeypatch.setenv(name, f"test-{name.lower()}-secret")
    return _set
