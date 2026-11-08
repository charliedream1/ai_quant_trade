"""Exercise real HTTP text-ReAct exchanges and research-team guardrails."""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
import yaml
from loguru import logger

from src.agent.research_protocol import run_role
from src.agent.research_team import CONFIG_PATH, ROLE_ORDER, ResearchTeam
from src.agent.skill_runner.service import LocalSkillService
from src.engine.backtest import BacktestRunner
from src.strategy import StrategyStore


@pytest.fixture
def protocol_provider():
    config = yaml.safe_load(Path("tests/agent/fixtures/research_team.yaml").read_text(encoding="utf-8"))
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            messages = payload["messages"]
            if len(messages) == 2:
                prompt = messages[-1]["content"]
                match = re.search(r"已有同事结果：(\[[^\n]*?\])", prompt)
                peers = json.loads(match.group(1)) if match else []
                required_match = re.search(r"本角色必须实际读取的证据：(\[[^\n]*?\])", prompt)
                required = json.loads(required_match.group(1)) if required_match else ["metrics"]
                calls = [*(("read_evidence", key) for key in required), *(("read_peer", role) for role in peers)]
                content = "\n".join(
                    "<tool_use>" + json.dumps({"name": name, "arguments": {"id": key}}) + "</tool_use>"
                    for name, key in calls
                )
            else:
                final = {key: config[key] for key in ("verdict", "summary", "concerns")}
                final["evidence_ids"] = ["metrics"]
                content = "<final>" + json.dumps(final, ensure_ascii=False).rstrip("}") + ",}</final>"
            body = json.dumps(
                {
                    "model": config["model"],
                    "choices": [{"message": {"content": content}}],
                    "usage": {"total_tokens": 10},
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            logger.debug(format, *args)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests, config
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _backtest():
    item = StrategyStore().import_example("egs/examples/strategy_examples/dual_ma_strategy.py")
    task = BacktestRunner().create(
        {
            "strategy_id": item["strategy_id"],
            "symbols": ["600519", "300750"],
            "start_date": "2026-01-05",
            "end_date": "2026-05-29",
            "initial_capital": 1000000,
        }
    )
    return task["task_id"]


def _etf_backtest():
    item = StrategyStore().import_example("egs/examples/strategy_examples/etf_momentum_rotation_strategy.py")
    task = BacktestRunner().create(
        {
            "strategy_id": item["strategy_id"],
            "parameter_profile": "etf_momentum.yaml:baseline",
            "params": {"universe": "cn_core"},
            "symbols": ["510300", "510500", "159915", "512100"],
            "start_date": "2026-01-05",
            "end_date": "2026-06-30",
            "initial_capital": 1000000,
            "order_type": "open",
        }
    )
    return task["task_id"]


@pytest.mark.parametrize("skill", ["quant-backtest-review", "quant-etf-review"])
def test_local_native_team_skill_reads_actual_backtest(client, protocol_provider, skill):
    url, requests, config = protocol_provider
    model = client.post(
        "/api/v1/llm-models", json={"name": "local-protocol", "model_name": config["model"], "base_url": url}
    ).json()["data"]
    task_id = _etf_backtest() if skill == "quant-etf-review" else _backtest()
    result = LocalSkillService().run(
        {
            "skill": skill,
            "provider": {"backend": "api", "model_id": model["model_id"]},
            "request": {"backtest_id": task_id, "objective": config["objective"]},
        }
    )
    assert result["status"] == "finished", result
    assert len(requests) == 8 and not result["result"]["can_trade"]


def test_four_agents_read_evidence_and_peers_over_plain_http(client, protocol_provider):
    url, requests, config = protocol_provider
    model = client.post(
        "/api/v1/llm-models",
        json={
            "name": "research-protocol",
            "model_name": config["model"],
            "base_url": url,
        },
    ).json()["data"]
    task_id = _backtest()
    response = client.post(
        "/api/v1/research-team/runs",
        json={
            "backtest_id": task_id,
            "objective": config["objective"],
            "model_id": model["model_id"],
        },
    ).json()
    assert response["code"] == 0
    report = response["data"]
    assert report["status"] == "finished", report.get("error")
    assert list(report["roles"]) == list(ROLE_ORDER)
    assert report["verdict"] == "watch", "synthetic results must not override hard checks"
    assert report["can_trade"] is False
    assert len(requests) == 8
    assert all("tools" not in body and "response_format" not in body for body in requests)
    chair_tools = report["roles"]["chair"]["tool_events"]
    assert {event["id"] for event in chair_tools if event["tool"] == "read_peer"} == set(ROLE_ORDER[:-1])
    saved = client.get(f"/api/v1/research-team/runs/{report['run_id']}").json()["data"]
    assert saved["roles"] == report["roles"]


def test_no_configured_model_fails_instead_of_mock_success(client):
    report = ResearchTeam().run(_backtest(), "核查成本与训练证据")
    assert report["status"] == "failed"
    assert "mock-llm" in report["error"]
    assert not report["roles"]


def test_cli_research_stream_consumes_real_protocol_events(cli_command, protocol_provider):
    url, requests, config = protocol_provider
    model = cli_command(
        "model", "create", "--name", "cli-research-protocol", "--model-name", config["model"], "--model-base-url", url
    )["data"]
    events = cli_command(
        "agent",
        "review",
        "--backtest-id",
        _backtest(),
        "--objective",
        config["objective"],
        "--model-id",
        model["model_id"],
        stream=True,
    )
    assert len(events) > 4 and events[-1]["type"] == "result"
    report = events[-1]["data"]["data"]
    assert report["status"] == "finished" and report["can_trade"] is False
    assert len(requests) == 8
    assert all("tools" not in body and "response_format" not in body for body in requests)
    assert cli_command("agent", "show", report["run_id"])["data"]["roles"] == report["roles"]


def test_etf_review_workflow_reads_etf_evidence_and_keeps_trade_gate_closed(client, protocol_provider):
    url, requests, config = protocol_provider
    model = client.post(
        "/api/v1/llm-models",
        json={"name": "etf-research-protocol", "model_name": config["model"], "base_url": url},
    ).json()["data"]
    response = client.post(
        "/api/v1/research-team/runs",
        json={
            "backtest_id": _etf_backtest(),
            "objective": "核查 ETF 池、流动性、换手、基准和跟踪误差",
            "model_id": model["model_id"],
            "workflow": "etf_review",
        },
    ).json()
    assert response["code"] == 0, response
    report = response["data"]
    assert report["status"] == "finished", report.get("error")
    assert report["workflow"] == "etf_review"
    assert report["evidence"]["etf"]["asset_type"] == "etf"
    assert report["can_trade"] is False
    assert list(report["roles"]) == list(ROLE_ORDER)
    assert len(requests) == 8


@pytest.mark.parametrize(
    "text",
    [
        '<final>{"verdict":"approve","summary":"ok","evidence_ids":["invented"],"concerns":[]}</final>',
        '<final>{"verdict":"approve","summary":"ok","evidence_ids":["metrics"],"concerns":[]}</final>',
        '<tool_use>{"name":"place_order","arguments":{"id":"metrics"}}</tool_use>',
    ],
)
def test_unread_or_invented_evidence_and_order_tools_are_rejected(text):
    class InvalidLLM:
        def complete(self, *args, **kwargs):
            return {"model": "fixture", "text": text}

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        run_role("analyst", "test", {"metrics": {}}, {}, config, InvalidLLM())


def test_invalid_report_id_has_business_error(client):
    result = client.get("/api/v1/research-team/runs/invalid-id").json()
    assert result["code"] == 1002


def test_chair_can_read_one_tool_per_turn_before_finishing():
    calls = [("read_evidence", "metrics"), *(("read_peer", role) for role in ROLE_ORDER[:-1])]
    replies = [
        "<tool_use>" + json.dumps({"name": name, "arguments": {"id": key}}) + "</tool_use>" for name, key in calls
    ]
    replies.append('<final>{"verdict":"watch","summary":"证据不足","evidence_ids":["metrics"],"concerns":[]}</final>')

    class SequentialLLM:
        def complete(self, *args, **kwargs):
            return {"model": "protocol-sequential-fixture", "text": replies.pop(0)}

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    result = run_role("chair", "test", {"metrics": {}}, {role: {} for role in ROLE_ORDER[:-1]}, config, SequentialLLM())
    assert len(result["tool_events"]) == 4
    assert result["verdict"] == "watch"
