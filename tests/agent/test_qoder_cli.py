"""Actual subprocess/protocol and durable API permission behavior without paid calls."""

import json
import sys
from pathlib import Path
from time import monotonic

import pytest
import yaml

from src.agent.composer_config import validate_selection
from src.agent.qoder_cli import QoderCliRunner
from src.agent.workspace import AIWorkspaceService
from src.core.exceptions import BusinessError
from src.frontend.services import FrontendService
from src.strategy.codex_cli import CodexCliRunner, CodexStreamEvent

FIXTURE = yaml.safe_load(
    Path(__file__).with_name("fixtures").joinpath("qoder_protocol.yaml").read_text(encoding="utf-8")
)


def test_real_command_flags_and_permission_deny_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("ALL_IN_ONE_QODER_CLI", sys.executable)
    runner = QoderCliRunner(project_root=tmp_path)
    command = runner.command("-", model="explicit-model", reasoning_effort="high", image_paths=[tmp_path / "图.png"])
    assert command[command.index("--permission-mode") + 1] == "dont_ask"
    assert command[command.index("--tools") + 1] == "Read,Glob,Grep"
    assert "--attachment" in command and "--strict-mcp-config" in command
    assert "--reasoning-effort" in command and command[-1] == "--print"
    assert "--dangerously-skip-permissions" not in command
    write = QoderCliRunner(project_root=tmp_path, access_mode="workspace-write").command("hello")
    assert write[write.index("--permission-mode") + 1] == "accept_edits"
    assert "Write" in write[write.index("--tools") + 1]
    codex = CodexCliRunner(project_root=tmp_path, access_mode="workspace-write")
    monkeypatch.setattr(codex, "executable", lambda: "codex-fixture")
    assert codex.command("hello")[5] == "workspace-write"


def test_qoder_native_deltas_complete_messages_and_result_do_not_duplicate():
    runner = QoderCliRunner()
    events = [runner.parse_event(row) for row in FIXTURE["events"]]
    assert "".join(row.text for row in events if row and row.kind == "message") == "你好，协议验证完成"
    error = runner.parse_event({"type": "result", "is_error": True, "result": "authentication required"})
    assert error.kind == "error" and error.status == "failed"


def test_real_subprocess_uses_stdin_and_reaps(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agent.qoder_cli.authentication_status", lambda *args, **kwargs: {"logged_in": True})
    runner = QoderCliRunner(project_root=tmp_path)
    fixture = Path(__file__).with_name("fixtures") / "qoder_protocol.yaml"
    script = (
        "import sys,json,yaml; from pathlib import Path; "
        "v=yaml.safe_load(Path(sys.argv[1]).read_text(encoding='utf-8')); "
        "assert sys.stdin.read()==v['message']; "
        "[sys.stdout.write(json.dumps(row,ensure_ascii=False)+'\\n') for row in v['events']]"
    )
    monkeypatch.setattr(runner, "command", lambda *args, **kwargs: [sys.executable, "-c", script, str(fixture)])
    events = list(runner.stream(FIXTURE["message"], stdin_prompt=True))
    assert "".join(row.text for row in events if row.kind == "message") == "你好，协议验证完成"
    assert events[-1].status == "completed"


def test_qoder_silent_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr("src.agent.qoder_cli.authentication_status", lambda *args, **kwargs: {"logged_in": True})
    runner = QoderCliRunner(project_root=tmp_path, timeout_seconds=3)
    monkeypatch.setattr(
        runner, "command", lambda *args, **kwargs: [sys.executable, "-c", "import time; time.sleep(20)"]
    )
    started = monotonic()
    assert list(runner.stream("hello"))[-1].status == "timeout"
    assert monotonic() - started < 8


def test_unauthenticated_cli_does_not_start_conversation(monkeypatch):
    monkeypatch.setattr("src.agent.qoder_cli.authentication_status", lambda *args, **kwargs: {"logged_in": False})
    runner = QoderCliRunner()
    monkeypatch.setattr(runner, "command", lambda *args, **kwargs: pytest.fail("Unauthenticated conversation started"))
    events = list(runner.stream("hello"))
    assert len(events) == 2 and events[0].status == "checking-auth"
    assert events[-1].status == "unavailable" and "未登录" in events[-1].text


def test_access_validation_before_messages_are_written(client):
    service = AIWorkspaceService()
    session = service.create_session("permission fixture")["id"]
    for payload in (
        {"backend": "qorder", "access_mode": "full-access"},
        {"backend": "generic", "access_mode": "workspace-write"},
    ):
        with pytest.raises(BusinessError, match="访问权限"):
            service.send(session, {"message": "hello", **payload})
    assert service.detail(session)["messages"] == []
    assert validate_selection({"backend": "qorder"})["backend"] == "qoder"
    rejected = client.post(
        f"/api/v1/ai-workspace/sessions/{session}/messages/stream",
        json={"message": "hello", "backend": "qoder", "access_mode": "full-access"},
    ).json()
    assert rejected["code"] != 0 and service.detail(session)["messages"] == []
    foreign = client.post(
        f"/api/v1/ai-workspace/sessions/{session}/messages",
        headers={"Origin": "https://external.invalid"},
        json={"message": "hello", "backend": "qoder", "access_mode": "workspace-write"},
    ).json()
    assert foreign["code"] != 0 and service.detail(session)["messages"] == []


def test_api_qoder_stream_permission_model_and_persistence(client, monkeypatch):
    observed = {}

    class ExplicitRunner:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        def stream(self, prompt, **kwargs):
            observed.update(kwargs)
            yield CodexStreamEvent("message", "completed", FIXTURE["message"])

    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "true")
    monkeypatch.setattr("src.agent.workspace_backend.QoderCliRunner", ExplicitRunner)
    session = client.post("/api/v1/ai-workspace/sessions", json={"title": "qoder-protocol"}).json()["data"]["id"]
    response = client.post(
        f"/api/v1/ai-workspace/sessions/{session}/messages/stream",
        json={
            "message": "hello",
            "backend": "qorder",
            "access_mode": "workspace-write",
            "model_name": "fixture-model",
            "reasoning_effort": "high",
        },
    )
    events = [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data:")]
    assert events[-1]["data"]["data"]["status"] == "completed"
    assert observed["access_mode"] == "workspace-write" and observed["model"] == "fixture-model"
    assert observed["reasoning_effort"] == "high" and observed["stdin_prompt"]
    messages = client.get(f"/api/v1/ai-workspace/sessions/{session}").json()["data"]["messages"]
    assert messages[0]["metadata"]["access_mode"] == messages[-1]["metadata"]["access_mode"] == "workspace-write"


def test_failed_backend_preserves_ui_input_and_attachments(client):
    result = list(FrontendService().ai_console_send_stream(0, "retry this", [], "qoder"))[-1]
    assert result[2] == "retry this" and result[3].get("__type__") == "update"
    assert "mock-disabled" in result[4]
