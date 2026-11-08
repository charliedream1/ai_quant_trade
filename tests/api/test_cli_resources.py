"""Missing UI-only capabilities now exposed through shared REST services."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.agent.workspace import AIWorkspaceService
from src.core.exceptions import BusinessError
from src.data.manager import current_market, set_current_market


def test_examples_pool_and_paper_account_routes(client):
    examples = client.get("/api/v1/strategy-examples").json()["data"]
    assert len(examples) >= 13
    response = client.post(
        "/api/v1/strategy-examples/import",
        json={"example": "egs/examples/strategy_examples/etf_momentum_rotation_strategy.py", "name": "cli-resource-import"},
    ).json()
    assert response["code"] == 0, response
    pool = client.post("/api/v1/resource-pools", json={"name": "cli-pool"}).json()["data"]
    imported = client.post(
        f"/api/v1/resource-pools/{pool['id']}/import",
        files={"file": ("universe.csv", b"symbol,weight\n510300,0.5\n510500,0.5\n")},
    ).json()
    assert imported["code"] == 0, imported
    assert imported["data"]["added"] == 2
    assert len(client.get(f"/api/v1/resource-pools/{pool['id']}/items").json()["data"]) == 2
    created = client.post("/api/v1/paper-accounts", json={"name": "cli-paper", "initial_capital": 100000}).json()[
        "data"
    ]
    assert client.get("/api/v1/paper-accounts").json()["data"]["items"][0]["account_id"] == created["account_id"]


def test_parallel_explicit_markets_do_not_change_ui_default(client):
    set_current_market("CN")

    def query(market):
        return client.get("/api/v1/system/capabilities", headers={"X-AIQuant-Market": market}).json()["data"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        cn, us = list(pool.map(query, ["CN", "US"]))
    assert cn["market"] == "CN"
    assert us["market"] == "US"
    assert current_market() == "CN"
    assert client.get("/api/v1/system/capabilities").json()["data"]["market"] == "CN"


def test_ai_workspace_upload_message_stream_and_history(client):
    session = client.post("/api/v1/ai-workspace/sessions", json={"title": "命令行研究", "project_name": "cli"}).json()[
        "data"
    ]
    uploaded = client.post("/api/v1/ai-workspace/attachments", files={"file": ("memo.md", "ETF说明".encode())}).json()[
        "data"
    ]
    response = client.post(
        f"/api/v1/ai-workspace/sessions/{session['id']}/messages/stream",
        json={"message": "分析附件", "backend": "generic", "attachments": [uploaded["attachment_id"]]},
    )
    events = [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data:")]
    assert events[0]["type"] == "status"
    assert events[-1]["type"] == "result"
    assert events[-1]["data"]["data"]["status"] == "mock"
    history = client.get(f"/api/v1/ai-workspace/sessions/{session['id']}").json()["data"]["messages"]
    assert [row["role"] for row in history] == ["user", "assistant"]
    assert history[-1]["metadata"]["attachments"]["count"] == 1


def test_ai_unavailable_backend_is_persisted_as_unavailable(client):
    session = client.post("/api/v1/ai-workspace/sessions", json={"title": "unavailable"}).json()["data"]
    result = client.post(
        f"/api/v1/ai-workspace/sessions/{session['id']}/messages",
        json={"message": "hello", "backend": "unregistered_cli"},
    ).json()
    assert result["data"]["status"] == "unavailable"
    assert result["data"]["session_id"] == session["id"]


def test_ai_session_rejects_overlapping_sends_and_saves_interruption(client):
    service = AIWorkspaceService()
    identifier = service.create_session("concurrent-cli")["id"]
    first = service.send_stream(identifier, {"message": "first"})
    assert next(first)["type"] == "status"
    with pytest.raises(BusinessError, match="上一条"):
        list(service.send_stream(identifier, {"message": "overlap"}))
    first.close()
    history = service.detail(identifier)["messages"]
    assert len(history) == 2 and history[-1]["metadata"]["status"] == "failed"
