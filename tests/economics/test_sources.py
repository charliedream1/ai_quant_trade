"""Public HTTP policy, revision caching and bounded source failures."""

import json
from contextlib import contextmanager

import pytest

from src.data import economics
from src.data.economics import EconomicDataSource
from src.engine.economics.store import EconomicStore


def test_source_cache_preserves_first_observation_and_versions(tmp_path, monkeypatch):
    provider = EconomicDataSource(EconomicStore(tmp_path))
    calls = []
    body = {"result": {"data": [{"REPORT_DATE": "2025-01-01", "NATIONAL_SAME": 1}]}}

    def request(*args):
        calls.append(args)
        return json.loads(json.dumps(body))

    monkeypatch.setattr(provider, "_request", request)
    first = provider.fetch("cpi")
    assert provider.fetch("cpi") == first and len(calls) == 1
    repeat = provider.fetch("cpi", refresh=True)
    assert repeat["version"] == first["version"]
    assert repeat["first_seen_at"] == first["first_seen_at"]
    body["result"]["data"][0]["NATIONAL_SAME"] = 2
    updated = provider.fetch("cpi", refresh=True)
    assert updated["version"] != first["version"]
    assert provider.store.read(first["version"])["raw"]["result"]["data"][0]["NATIONAL_SAME"] == 1


def test_injected_security_filter_is_rejected_before_network(tmp_path, monkeypatch):
    provider = EconomicDataSource(EconomicStore(tmp_path))
    monkeypatch.setattr(provider, "_request", lambda *args: pytest.fail("Network must not run"))
    with pytest.raises(ValueError, match="identifier"):
        provider.fetch("income", symbol='600519.SH") OR (1=1')


def test_bounded_http_refuses_redirects_and_oversized_responses(tmp_path, monkeypatch):
    provider = EconomicDataSource(EconomicStore(tmp_path))
    config = {**provider.config, "defaults": {**provider.config["defaults"], "max_response_bytes": 3}}
    provider.config = config
    seen = []

    class Response:
        status_code = 302

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"long"

    response = Response()

    class Session:
        def request(self, *args, **kwargs):
            seen.append(kwargs)
            return response

    @contextmanager
    def session(**kwargs):
        assert kwargs == {"public_only": True}
        yield Session()

    monkeypatch.setattr(economics, "network_session", session)
    with pytest.raises(ValueError, match="redirect"):
        provider._request("https://example.com", {}, False)
    response.status_code = 200
    with pytest.raises(ValueError, match="budget"):
        provider._request("https://example.com", {}, False)
    assert all(row["allow_redirects"] is False for row in seen)
