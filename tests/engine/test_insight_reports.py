"""Executable report contracts, streaming boundaries, and failure safety."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread

import pytest
import yaml

from src.agent.skill_runner.service import LocalSkillService
from src.engine.insights.config import insight_config, load_skill
from src.engine.insights.research import parse_report, run_research
from src.engine.insights.service import InsightReportService
from src.strategy.codex_cli import CodexCliRunner

FIXTURE = yaml.safe_load(
    Path(__file__).with_name("fixtures").joinpath("insight_reports.yaml").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("skill", ["quant-market-review", "quant-stock-analysis"])
def test_local_native_insight_entry_preserves_domain_html(client, adapter, skill):
    result = LocalSkillService().run({"skill": skill, "request": {"symbol": str(FIXTURE["symbols"][0])}})
    assert result["status"] == "partial", result
    report = LocalSkillService().store.directory(result["run_id"]) / "report.html"
    assert FIXTURE["report"]["summary"] in report.read_text(encoding="utf-8")


def report_text(kind):
    config = insight_config()
    report = FIXTURE["report"]
    return json.dumps(
        {
            **report,
            "sections": [
                {"heading": heading, "paragraphs": [report["paragraph"]], "source_ids": ["E1"]}
                for heading in config["tasks"][kind]["sections"]
            ],
        },
        ensure_ascii=False,
    )


@pytest.fixture()
def adapter(monkeypatch):
    from src.engine.insights import execution

    monkeypatch.setattr(execution, "validate_backend", lambda *args: None)

    def generate(prompt, payload, config, emit):
        emit("message", FIXTURE["report"]["summary"])
        return report_text(payload["kind"])

    monkeypatch.setattr(execution, "generate_text", generate)
    return execution


@pytest.mark.parametrize("kind", ["market_review", "single_stock_analysis"])
def test_report_pipeline_and_http_artifacts(client, adapter, kind):
    payload = {"kind": kind, "backend": "api", "symbol": str(FIXTURE["symbols"][0])}
    response = client.post("/api/v1/insights/runs/stream", json=payload)
    assert response.status_code == 200
    stream = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    run = stream[-1]["data"]["data"]
    assert run["status"] == "partial", run
    assert run["skills"]["SKILL.md"]
    assert any(event["data"].get("kind") == "message" for event in stream[:-1])
    report = client.get(f"/api/v1/insights/runs/{run['run_id']}/files/report.html")
    assert report.status_code == 200
    assert "plotly" in report.text and FIXTURE["report"]["summary"] in report.text
    assert "attachment" in report.headers["content-disposition"]
    assert client.get(f"/api/v1/insights/runs/{run['run_id']}/files/run.json").status_code == 404
    events = client.get(f"/api/v1/insights/runs/{run['run_id']}/events").json()["data"]
    assert any(event["kind"] == "tool" and event["data"]["status"] == "completed" for event in events)
    assert client.get("/api/v1/insights/runs").json()["data"][0]["run_id"] == run["run_id"]


def test_duplicate_request_reuses_job_and_missing_backend_fails(client, monkeypatch, adapter):
    entered, finish = Event(), Event()

    def generate(prompt, payload, config, emit):
        entered.set()
        assert finish.wait(10)
        return report_text(payload["kind"])

    monkeypatch.setattr(adapter, "generate_text", generate)
    service = InsightReportService()
    payload = {"kind": "market_review", "backend": "api"}
    first = service.start(payload)
    assert entered.wait(10)
    try:
        second = service.start(payload)
        assert first["run_id"] == second["run_id"]
    finally:
        finish.set()
    assert list(service.follow(first["run_id"]))[-1]["run"]["status"] == "partial"

    def unavailable(*args):
        raise ValueError(service.config["messages"]["unavailable"])

    monkeypatch.setattr(adapter, "validate_backend", unavailable)
    run = service.start(payload)
    result = list(service.follow(run["run_id"]))[-1]["run"]
    assert result["status"] == "failed" and result["error"]
    with pytest.raises(ValueError):
        service.store.artifact(run["run_id"], "report.html")


def test_cli_stream_and_skill_registry_share_executor(cli_command, adapter):
    from src.integration.skill_manager import SkillManager

    events = cli_command("insight", "run", "--kind", "market_review", "--backend", "api", stream=True)
    assert any(event.get("type") == "progress" for event in events)
    skills = SkillManager()
    skill = next(row for row in skills.list() if row["name"] == "single_stock_analysis")
    skills.enable(skill["skill_id"], True)
    run = skills.run(skill["skill_id"], {"backend": "api", "symbol": str(FIXTURE["symbols"][0])})
    assert list(InsightReportService().follow(run["run_id"]))[-1]["run"]["status"] == "partial"


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "unknown"},
        {"kind": "market_review", "backend": "unconnected"},
        {"kind": "single_stock_analysis"},
        {"kind": "market_review", "end_date": "invalid"},
    ],
)
def test_invalid_requests_do_not_start_tasks(client, payload):
    with pytest.raises(ValueError):
        InsightReportService().start(payload)


def test_textual_react_and_repaired_json_only_accept_attributable_sections():
    config = insight_config()
    skill, resources = load_skill("market_review", config)
    evidence = {"sources": [{"id": "E1", "data": {}}]}
    observed, prompts = [], []

    def generate(prompt, payload, config, emit):
        return FIXTURE["tool"] if "工具观察" not in prompt else report_text(payload["kind"]).rstrip("}") + ",}"

    report = run_research(
        {"kind": "market_review", "backend": "api"},
        evidence,
        skill,
        resources,
        config,
        lambda *args: observed.append(args),
        prompts.append,
        generate,
    )
    assert report["summary"]
    assert len(prompts) == 2 and any(event[0] == "observation" for event in observed)
    invalid = json.loads(report_text("market_review"))
    invalid["sections"][0]["source_ids"] = [{"invalid": "unhashable"}]
    with pytest.raises(ValueError):
        parse_report(json.dumps(invalid), evidence, config, "market_review")


def test_report_escapes_model_html_and_isolates_preview(client, adapter, monkeypatch):
    from src.frontend.service.insights import _view

    def generate(prompt, payload, config, emit):
        report = json.loads(report_text(payload["kind"]))
        report["summary"] = FIXTURE["hostile"]
        return json.dumps(report)

    monkeypatch.setattr(adapter, "generate_text", generate)
    service = InsightReportService()
    run = service.start({"kind": "market_review"})
    run = list(service.follow(run["run_id"]))[-1]["run"]
    html = service.store.artifact(run["run_id"], "report.html").read_text(encoding="utf-8")
    assert FIXTURE["hostile"] not in html and "&lt;script&gt;" in html
    preview = _view(service, run, service.store.events(run["run_id"]))[2]
    assert 'sandbox="allow-scripts"' in preview and "allow-same-origin" not in preview
    with pytest.raises(ValueError):
        service.store.artifact("../../outside", "report.html")


def test_codex_large_prompt_uses_stdin_without_command_line_limit(monkeypatch, tmp_path):
    prompt = "中文" * insight_config()["defaults"]["max_skill_chars"]
    monkeypatch.setattr(
        CodexCliRunner,
        "command",
        lambda self, text, **kwargs: [
            sys.executable,
            "-c",
            "import sys,json; text=sys.stdin.buffer.read().decode('utf-8'); "
            "sys.stdout.buffer.write((json.dumps({'type':'item.completed','item':{'type':'agent_message','text':str(len(text))}})+'\\n').encode())",
        ],
    )
    events = list(CodexCliRunner(project_root=tmp_path).stream(prompt, stdin_prompt=True))
    assert any(event.text == str(len(prompt)) for event in events)
    assert not any(event.kind == "error" for event in events)


def test_actual_http_sse_streams_without_function_call(client):
    from src.core.repository import Repository
    from src.engine.insights.backend import generate_text

    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            text = FIXTURE["report"]["summary"]
            for fragment in (text[:2], text[2:]):
                self.wfile.write(
                    ("data: " + json.dumps({"choices": [{"delta": {"content": fragment}}]}) + "\n\n").encode()
                )
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        from src.core.timeutil import utc_now_iso

        model = Repository().insert(
            "llm_models",
            {
                "name": "insight-sse-test",
                "model_name": "test",
                "api_key": "",
                "purpose": "research",
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "enabled": 1,
            },
        )
        events = []
        result = generate_text(
            "protocol-test",
            {"backend": "api", "model_id": model["id"]},
            insight_config(),
            lambda *args: events.append(args),
        )
        assert result == FIXTURE["report"]["summary"] and len(events) == 2
        assert requests[0]["stream"] and "tools" not in requests[0] and "response_format" not in requests[0]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(5)
