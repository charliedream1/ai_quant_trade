"""Executable regressions for the code-health audit's trust and async boundaries."""

import asyncio
import time
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.security import AccessControl, access_options
from src.core.config import Settings
from src.core.redaction import redact
from src.strategy.strategy_store import StrategyStore


def test_foreign_origin_rejected_for_read_and_write(client):
    for method, path, payload in (
        ("GET", "/api/v1/mcp-servers", None),
        ("POST", "/api/v1/mcp-servers", {"name": "refused"}),
    ):
        response = client.request(method, path, json=payload, headers={"Origin": "https://untrusted.invalid"})
        assert response.status_code == 403


def test_localhost_and_token_access_modes(monkeypatch):
    app = FastAPI()

    @app.get("/private")
    def private():
        return {"ok": True}

    monkeypatch.setenv("ALL_IN_ONE_ACCESS_MODE", "token")
    token = "explicit-test-access-token-not-a-real-credential"
    monkeypatch.setenv("ALL_IN_ONE_ACCESS_TOKEN", token)
    options = access_options(Settings(data_mode="mock"))
    app.add_middleware(AccessControl, options=options)
    with TestClient(app) as client:
        assert client.get("/private").status_code == 401
        assert client.get("/private", headers={"Authorization": "Bearer " + token}).status_code == 200
        assert client.post("/access/login", data={"token": token}, follow_redirects=False).status_code == 303
        assert client.get("/private").status_code == 200
        assert client.get("/private", headers={"Host": "attacker.invalid"}).status_code == 403


def test_mcp_configuration_redacts_credentials_and_preserves_usage(client):
    value = {
        "name": "redaction",
        "transport": "http",
        "url": "http://127.0.0.1:1",
        "headers": {"Authorization": "Bearer synthetic-audit-value"},
        "env": {"EXAMPLE_API_KEY": "test-value"},
    }
    response = client.post("/api/v1/mcp-servers", json=value).json()
    assert response["code"] == 0
    shown = client.get("/api/v1/mcp-servers").text
    assert "synthetic-audit-value" not in shown and "test-value" not in shown
    assert redact({"total_tokens": 42}) == {"total_tokens": 42}


def test_strategy_create_and_read_do_not_execute_source(client, tmp_path):
    marker = tmp_path / "must-not-exist.txt"
    code = (
        "import builtins\nbuiltins.open("
        + repr(str(marker))
        + ", 'w').write('unexpected')\ndef on_bar(event, context):\n    return []\n"
    )
    item = StrategyStore().create({"name": "static-only", "code": code})
    assert not marker.exists()
    assert StrategyStore().get(item["id"])["interface_report"]["execution"] == "not_started"
    assert not marker.exists()


def test_validation_failure_is_serializable_and_internal_errors_are_private(client):
    response = client.post(
        "/api/v1/alpha/studies",
        json={"name": "audit", "dataset_id": 1, "models": {"default": {"backend": "qoder", "model_id": 1}}},
    ).json()
    assert response["code"] == 1002
    assert "not JSON serializable" not in str(response)

    @client.app.get("/__test_failure")
    def failure():
        raise RuntimeError("internal-only-private-marker")

    with TestClient(client.app, raise_server_exceptions=False) as safe:
        result = safe.get("/__test_failure").json()
    assert result["code"] == 5999 and result["data"] is None and "internal-only" not in str(result)


def test_async_upload_does_not_block_event_loop(client):
    from src.agent.workspace import AIWorkspaceService

    def slow(self, filename, content):
        time.sleep(0.15)
        return {"attachment_id": "fixture"}

    async def measure():
        samples = []
        finished = asyncio.Event()

        async def heartbeat():
            while not finished.is_set():
                started = time.perf_counter()
                await asyncio.sleep(0.005)
                samples.append(time.perf_counter() - started)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=client.app), base_url="http://testserver"
        ) as http:
            pulse = asyncio.create_task(heartbeat())
            await asyncio.sleep(0.02)
            with patch.object(AIWorkspaceService, "upload", slow):
                result = await http.post("/api/v1/ai-workspace/attachments", files={"file": ("audit.txt", b"ok")})
            finished.set()
            await pulse
            assert result.json()["code"] == 0
        return max(samples)

    assert asyncio.run(measure()) < 0.1
