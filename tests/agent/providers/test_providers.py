"""Native process lifecycle, frozen identity and role boundary regressions."""

import json
import sys
from pathlib import Path
from threading import Event, Timer
from time import monotonic

import pytest

from src.agent.providers import ProviderClient
from src.agent.providers.config import provider_config
from src.agent.providers.events import check_research_event, collect_response
from src.agent.providers.native import NativeCliRunner, ResearchQoderRunner
from src.agent.providers.registry import check_identity, require_native
from src.strategy.codex_cli import CodexCliRunner, CodexStreamEvent


class FixtureRunner(ResearchQoderRunner):
    def __init__(self, directory, case):
        super().__init__(directory, 3)
        self.case = case

    def command(self, prompt, **kwargs):
        return [sys.executable, str(Path(__file__).parent / "fixtures/process.py"), self.case]


def native_fixture(monkeypatch, case):
    monkeypatch.setattr(
        FixtureRunner, "stream", lambda self, *args, **kwargs: CodexCliRunner.stream(self, *args, **kwargs)
    )
    state = {
        "backend": "qoder",
        "version": "fixture-only",
        "model_name": "fixture-native-model",
        "strict_supported": True,
    }
    monkeypatch.setattr("src.agent.providers.service.require_native", lambda *args, **kwargs: state)
    monkeypatch.setattr(
        "src.agent.providers.service.runner_for", lambda backend, directory, timeout: FixtureRunner(directory, case)
    )


def test_api_preserves_injection_and_selection():
    observed = []

    class API:
        def complete(self, prompt, **kwargs):
            observed.append(kwargs)
            return {"text": prompt, "model": "fixture-api"}

    result = ProviderClient(API()).complete(
        "中文", selection={"model_id": 7, "reasoning_effort": "low"}, purpose="test"
    )
    assert result["backend"] == "api" and result["usage"] is None
    assert observed == [{"model_id": 7, "reasoning_effort": "low", "purpose": "test"}]


def test_actual_native_process_text_unicode_and_usage(client, monkeypatch):
    native_fixture(monkeypatch, "plain")
    seen = []
    result = ProviderClient().complete(
        "已冻结的中文证据", selection={"backend": "qoder"}, emit=lambda *args: seen.append(args)
    )
    assert json.loads(result["text"])["verdict"] == "watch"
    assert result["model"] == "fixture-native-model" and result["usage"]["output_tokens"] == 5
    assert Path(result["artifact_dir"], "events.json").is_file()
    assert any(row[0] == "message" for row in seen)


@pytest.mark.parametrize("case,match", [("tool", "原生能力"), ("unknown", "未核验"), ("error", "fixture-auth-error")])
def test_native_tool_unknown_and_error_refused(client, monkeypatch, case, match):
    native_fixture(monkeypatch, case)
    with pytest.raises(ValueError, match=match):
        ProviderClient().complete("evidence", selection={"backend": "qoder"})


def test_silent_process_cancel_is_bounded(client, monkeypatch):
    native_fixture(monkeypatch, "silent")
    cancel = Event()
    timer = Timer(0.5, cancel.set)
    timer.start()
    started = monotonic()
    try:
        with pytest.raises(ValueError):
            ProviderClient().complete("evidence", selection={"backend": "qoder"}, cancelled=cancel.is_set)
    finally:
        timer.cancel()
    assert monotonic() - started < 5


def test_recursion_never_starts_native_process(client, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_PROVIDER_DEPTH", "1")
    with pytest.raises(ValueError, match="递归"):
        ProviderClient().complete("evidence", selection={"backend": "qoder"})


def test_qoder_research_command_disables_native_tools_and_discovery(monkeypatch, tmp_path):
    monkeypatch.setattr(ResearchQoderRunner, "executable", lambda self: sys.executable)
    command = ResearchQoderRunner(tmp_path).command("-", model="verified-model", reasoning_effort="low")
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--setting-sources") + 1] == ""
    assert command[command.index("--mcp-config") + 1] == '{"mcpServers":{}}'
    assert "--system-prompt" in command and "--no-session-persistence" in command


def test_trae_legacy_does_not_receive_v2_flags(tmp_path):
    runner = NativeCliRunner("trae", tmp_path, 5, "trae-cli version 0.120.42")
    runner.executable = lambda: sys.executable
    command = runner.command("-")
    assert "--print" in command and "exec" not in command and "--ignore-user-config" not in command
    with pytest.raises(ValueError, match="未核验"):
        runner.command("-", model="unsupported")
    newer = NativeCliRunner("trae", tmp_path, 5, "trae-cli version 2.1.0")
    newer.executable = lambda: sys.executable
    assert "exec" in newer.command("-")


def test_unverified_cli_and_frozen_identity_fail_before_generation(monkeypatch):
    monkeypatch.setattr(
        "src.agent.providers.registry.provider_snapshot",
        lambda *args, **kwargs: {
            "backend": "codex",
            "installed": True,
            "strict_supported": False,
            "strict_reason": "fixture",
        },
    )
    with pytest.raises(ValueError, match="严格研究"):
        require_native({"backend": "codex"})
    with pytest.raises(ValueError, match="冻结身份"):
        check_identity({"backend": "api", "model_name": "before"}, {"backend": "api", "model_name": "after"})


def test_streamed_native_tool_is_rejected_before_assistant_completion():
    with pytest.raises(ValueError, match="原生工具"):
        check_research_event({"raw": {"type": "stream_event", "event": {"delta": {"type": "input_json_delta"}}}})
    assert provider_config()["providers"]["trae"]["strict"] is False


def test_missing_initialization_cannot_prove_strict_role_mode():
    with pytest.raises(ValueError, match="初始化事件"):
        collect_response(
            iter([CodexStreamEvent("message", "running", "unverified")]),
            "qoder",
            provider_config(),
            None,
            None,
            1000,
            [],
        )
