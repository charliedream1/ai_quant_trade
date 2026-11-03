"""Explicit opt-in live Codex audit; never collected during the routine suite."""

import json
from pathlib import Path


def test_live_codex_events_and_durable_session(cli_command, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "true")
    monkeypatch.setenv("ALL_IN_ONE_CODEX_TIMEOUT_SECONDS", "60")
    session = cli_command("ai", "session", "create", "--title", "CLI真实Codex验收")["data"]["id"]
    events = cli_command(
        "ai",
        "ask",
        "--session-id",
        session,
        "--backend",
        "codex",
        "--message",
        "请只回复：你好，CLI端到端验证成功。不要运行工具，不要读写文件。",
        "--reasoning-effort",
        "low",
        "--require-real",
        stream=True,
        timeout=90,
    )
    assert events[-1]["type"] == "result"
    result = events[-1]["data"]["data"]
    assert result["status"] == "completed" and result["text"]
    assert any(event["type"] == "message" for event in events)
    history = cli_command("ai", "session", "show", session)["data"]["messages"]
    assert history[-1]["content"] == result["text"]
    report = {"kind": "live_codex_cli_http", "events": events, "history_count": len(history)}
    target = Path(__file__).resolve().parents[2] / "docs/audit/cli_codex_validation_2026-10-20.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
