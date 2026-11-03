"""Native artifact round trips, actual HTTP ReAct, strict replay and lifecycle guards."""

import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from time import perf_counter

import pytest
import yaml
from loguru import logger

from src.agent.decision_team import DecisionTeam, validate_decision
from src.data.eastmoney import EastmoneyDataSource
from src.engine.composition.agent_gateway import AgentGateway
from src.strategy import codex_cli
from src.strategy.codex_cli import CodexCliRunner
from src.strategy.components.models import ScoreModel
from src.strategy.composition.accounts import PipelineAccounts
from src.strategy.composition.config import template
from src.strategy.composition.contracts import Frame, Observation
from src.strategy.composition.model_artifacts import ModelArtifacts
from src.strategy.composition.service import PipelineService
from src.strategy.composition.store import PipelineStore
from src.strategy.composition.validation import compile_plan, digest

from .market_fixture import small_models, snapshot

AGENT = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("agent.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("component", ["lightgbm", "xgboost", "mlp"])
def test_native_artifact_reloads_identical_predictions_without_fitting(client, component):
    data = snapshot()
    plan = small_models(compile_plan(template("parallel_three_model")))
    params = next(node["params"] for node in plan["nodes"] if node["component"] == component)
    day = max(row["date"] for rows in data["history"].values() for row in rows)
    frame = Frame.create(day, data["history"])
    artifacts = ModelArtifacts()
    fitted = ScoreModel(component, params, artifacts)
    original = fitted.predict(sorted(data["history"]), frame, lambda *args: None)
    events = []
    restored = ScoreModel(component, params, artifacts)
    loaded = restored.predict(sorted(data["history"]), frame, lambda *args: events.append(args))
    assert {s: r.value for s, r in loaded.items()} == pytest.approx({s: r.value for s, r in original.items()})
    assert restored.diagnostics["fits"][0]["actual_fit"] is False
    assert all(row[0] != "model_fit" for row in events)
    assert any(row[0] == "model_cache" for row in events)
    metadata = artifacts.metadata(restored.diagnostics["fits"][0]["artifact"]["id"])
    assert metadata and metadata["format"] != "pickle"


@pytest.fixture
def provider():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            prompt = payload["messages"][-1]["content"]
            text = json.dumps(AGENT["result"], ensure_ascii=False) if "实际工具观察" in prompt else AGENT["tool"]
            body = (
                "data: " + json.dumps({"choices": [{"delta": {"content": text}}]}) + "\n\ndata: [DONE]\n\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            logger.debug(format, *args)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def test_three_role_agent_uses_actual_text_stream_and_registered_readonly_tool(client, provider):
    url, requests = provider
    model = client.post(
        "/api/v1/llm-models", json={"name": AGENT["model"], "model_name": AGENT["model"], "base_url": url}
    ).json()["data"]
    events = []
    result = DecisionTeam({"backend": "api", "model_id": model["model_id"]}, lambda *args: events.append(args)).decide(
        AGENT["as_of"], AGENT["candidates"], AGENT["holdings"], {"E1": {}, "E2": {}, "E3": {}}, "committee"
    )
    assert result["decisions"] == AGENT["result"]["decisions"]
    assert len(result["roles"]) == 3 and len(requests) == 6
    assert all(row["stream"] and "tools" not in row and "response_format" not in row for row in requests)
    assert sum(row[0] == "agent_tool" for row in events) == 3
    assert any(row[0] == "message" for row in events)


def test_agent_replay_requires_exact_evidence_and_original_timestamp(client, monkeypatch):
    store = PipelineStore()
    frame = Frame.create(AGENT["as_of"], {}, account={"positions": {"600519": 1}})
    scores = {s: Observation(s, 1.0) for s in AGENT["candidates"]}

    def decide(self, as_of, candidates, holdings, evidence, workflow):
        return {
            **deepcopy(AGENT["result"]),
            "generated_at": as_of + "T12:00:00+00:00",
            "valid_until": as_of + "T23:59:59+00:00",
            "input_digest": digest(
                {"as_of": as_of, "candidates": candidates, "holdings": holdings, "evidence": evidence}
            ),
        }

    monkeypatch.setattr(DecisionTeam, "decide", decide)
    node = {"id": "review", "params": {"workflow": "single"}}
    original = AgentGateway({"agent_mode": "live"}, store, lambda *args: None, "main")(node, frame, scores)
    replay = AgentGateway({"agent_mode": "replay", "agent_replay": [original["id"]]}, store, lambda *args: None, "main")
    assert replay(node, frame, scores)["id"] == original["id"]
    with pytest.raises(ValueError):
        replay(node, Frame.create(frame.as_of, {}, account={"positions": {}}), scores)
    path = store.root / "decisions" / (original["id"] + ".json")
    original["generated_at"] = datetime.now(UTC).isoformat()
    path.write_text(json.dumps(original), encoding="utf-8")
    with pytest.raises(ValueError):
        replay(node, frame, scores)


def test_disable_blocks_new_decisions_and_compare_and_swap_rejects_stale_writer(client):
    service = PipelineService()
    draft = service.store.save_draft(template("rule_trend"))
    version = service.store.publish(draft["id"])
    service.store.set_enabled(draft["id"], False)
    with pytest.raises(ValueError, match="disabled"):
        service.start({"version_id": version["id"], "mode": "targets", "agent_mode": "off"})
    # Immutable versions remain inspectable after disabling a plan.
    assert service.store.version(version["id"], True)["id"] == version["id"]
    account = PipelineAccounts(service.store).create(version["id"], "CAS validation")
    service.store.save_account(account["id"], account["version"], account["state"], "")
    with pytest.raises(ValueError, match="concurrently"):
        service.store.save_account(account["id"], account["version"], account["state"], "")


def test_cli_pipeline_waits_for_terminal_json_and_maps_require_real(cli_command, tmp_path):
    result = cli_command("pipeline", "run", "--template", "rule_trend", "--mode", "targets", "--agent-mode", "off")
    assert result["data"]["status"] == "finished"
    preview = cli_command("--require-real", "--dry-run", "pipeline", "run", "--template", "rule_trend")
    assert preview["data"]["body"]["require_real"] is True
    output = tmp_path / "pipeline-result.json"
    saved = cli_command(
        "pipeline",
        "run",
        "--template",
        "rule_trend",
        "--mode",
        "targets",
        "--agent-mode",
        "off",
        "--output",
        str(output),
    )
    assert output.is_file() and json.loads(output.read_text(encoding="utf-8"))["data"]["id"] == saved["data"]["id"]


def test_invalid_agent_cannot_invent_symbols_or_skip_candidates():
    result = deepcopy(AGENT["result"])
    result["decisions"].pop(0)
    with pytest.raises(ValueError):
        validate_decision(json.dumps(result), AGENT["candidates"], AGENT["holdings"], {"E1": {}, "E3": {}})


def test_invalid_pipeline_configuration_is_a_parameter_error(client):
    response = client.post("/api/v1/strategy-pipelines/preview", json={"definition": {}}).json()
    assert response["code"] == 1002


def test_cancel_terminates_a_silent_owned_cli_process(monkeypatch):
    processes = []
    real_popen = codex_cli.subprocess.Popen

    def spawn(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(codex_cli.subprocess, "Popen", spawn)
    runner = CodexCliRunner()
    monkeypatch.setattr(
        runner,
        "command",
        lambda *args, **kwargs: [sys.executable, "-c", "import threading; threading.Event().wait(60)"],
    )
    cancelled = False
    stream = runner.stream("", cancelled=lambda: cancelled)
    assert next(stream).status == "running"
    cancelled = True
    started = perf_counter()
    list(stream)
    assert perf_counter() - started < 3
    assert processes and all(process.poll() is not None for process in processes)


def test_strategy_market_path_does_not_fetch_unrelated_news_or_reports(monkeypatch):
    provider = EastmoneyDataSource()

    def forbidden(*args, **kwargs):
        raise AssertionError("Strategy market snapshot must not fetch reports/news")

    monkeypatch.setattr(provider, "reports", forbidden)
    monkeypatch.setattr(provider, "_stock_news", forbidden)
    monkeypatch.setattr(provider, "stock_quote", lambda *args: {"industry": "test-sector"})
    monkeypatch.setattr(provider, "_kline", lambda *args: [])
    result = provider.strategy_snapshot(AGENT["candidates"][0])
    assert result["industry"] == "test-sector" and "reports" not in result and "news" not in result
