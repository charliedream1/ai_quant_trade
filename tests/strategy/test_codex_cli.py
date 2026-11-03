"""Codex CLI command and JSONL event parsing tests."""

import sys
from pathlib import Path
from time import monotonic

from src.strategy.codex_cli import CodexCliRunner


def test_codex_command_is_read_only_and_forwards_model_reasoning(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ALL_IN_ONE_CODEX_CLI", "codex-test")
    command = CodexCliRunner(project_root=tmp_path).command(
        "你好",
        model="gpt-test",
        reasoning_effort="high",
        image_paths=[tmp_path / "image.png"],
    )
    assert command[:4] == ["codex-test", "exec", "--json", "--ephemeral"]
    assert "--sandbox" in command and command[command.index("--sandbox") + 1] == "read-only"
    assert ["--model", "gpt-test"] == command[command.index("--model") : command.index("--model") + 2]
    assert ["--config", "model_reasoning_effort=high"] == command[
        command.index("--config") : command.index("--config") + 2
    ]
    assert "--image" in command
    assert command[-1] == "你好"


def test_silent_cli_child_times_out_and_is_reaped(monkeypatch, tmp_path):
    runner = CodexCliRunner(project_root=tmp_path, timeout_seconds=3)
    monkeypatch.setattr(
        runner, "command", lambda *args, **kwargs: [sys.executable, "-c", "import time; time.sleep(30)"]
    )
    started = monotonic()
    events = list(runner.stream("hello"))
    assert events[-1].kind == "error" and events[-1].status == "timeout"
    assert monotonic() - started < 8
