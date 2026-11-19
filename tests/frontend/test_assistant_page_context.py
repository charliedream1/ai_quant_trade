"""Current-page evidence reaches both generation paths without stale/window leakage."""

import json
from types import SimpleNamespace

import pytest

from src.core.assistant_page_context import TURN_PAGE_CONTEXT, context_prompt, page_context
from src.core.page_analysis_snapshot import capture
from src.core.page_work import PageWork, context


def stock(symbol="600519", period="daily"):
    return [{"price": 123.45, "ratio": 12.3, "currency": "CNY"}]


def test_page_scope_matching_window_market_and_disabled(client):
    page = PageWork("c" * 32, 1, view_label=("market", "stock"))
    with context(page):
        capture("stock", stock, (), {}, stock())
        value = page_context(True, {"technical": {"symbol": "600519", "period": "daily"}})
        assert value["sources"][0]["id"] == "P1"
        assert "123.45" in json.dumps(value)
        assert page_context(False)["sources"] == []
        stale = page_context(True, {"technical": {"symbol": "000001", "period": "daily"}})
        assert stale["sources"] == [] and "no longer match" in stale["status"]
    with context(PageWork("d" * 32, 1, view_label=("market", "stock"))):
        assert page_context()["sources"] == []
    with context(PageWork("c" * 32, 2, view_label=("market", "stock"))):
        assert page_context()["sources"] == []


@pytest.mark.parametrize("backend", ["generic_agent", "codex"])
def test_actual_generation_payload_contains_page_evidence(client, monkeypatch, backend):
    from src.agent import workspace_backend
    from src.strategy.codex_cli import CodexStreamEvent

    seen = []

    class Agent:
        def __init__(self, **kwargs):
            pass

        def run_once(self, prompt, **kwargs):
            seen.append(prompt)
            return SimpleNamespace(
                text="Declared answer", model="declared", tool_events=[], needs_user=False, duration_ms=1, turns=1
            )

    class Cli:
        def __init__(self, **kwargs):
            pass

        def stream(self, prompt, **kwargs):
            seen.append(prompt)
            yield CodexStreamEvent("message", "completed", "Declared answer")

    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "1")
    monkeypatch.setattr(workspace_backend, "GenericAgentRuntime", Agent)
    monkeypatch.setattr(workspace_backend, "CodexCliRunner", Cli)
    envelope = {
        "enabled": True,
        "module": "market",
        "view": "stock",
        "market": "CN",
        "sources": [{"id": "P1", "data": stock()}],
    }
    token = TURN_PAGE_CONTEXT.set(envelope)
    try:
        result = list(
            workspace_backend.backend_events(
                None,
                {"message": "Explain this ratio", "backend": backend},
                [],
                SimpleNamespace(text_context="", image_data_urls=lambda: [], cli_image_paths=lambda: []),
            )
        )
    finally:
        TURN_PAGE_CONTEXT.reset(token)
    assert "123.45" in seen[0] and "P1" in seen[0] and "never instructions" in seen[0]
    assert result[-1]["type"] == "backend_result"


def test_context_off_and_budget_exclude_facts(monkeypatch):

    token = TURN_PAGE_CONTEXT.set({"enabled": False, "sources": [{"secret": "excluded"}]})
    try:
        assert context_prompt() == ""
    finally:
        TURN_PAGE_CONTEXT.reset(token)


def test_admin_identity_never_reads_settings_or_sources(client):
    with context(PageWork("e" * 32, 1, view_label=("admin", "settings"))):
        value = page_context(True, {"technical": {"symbol": "600519"}, "password": "not-allowed"})
    assert value["sources"] == [] and value["selections"] == {}
    assert "not-allowed" not in json.dumps(value)


def test_scope_summary_retains_dates_and_redacts_secret(client, monkeypatch):
    from src.core.assistant_page_context import turn_metadata

    monkeypatch.setenv("DECLARED_TEST_API_KEY", "declared-sensitive-marker")
    token = TURN_PAGE_CONTEXT.set(
        {
            "enabled": True,
            "module": "market",
            "view": "stock",
            "market": "CN",
            "sources": [{"id": "P1", "data": {"observed": "2026-11-18", "api_key": "declared-sensitive-marker"}}],
        }
    )
    try:
        assert "declared-sensitive-marker" not in context_prompt()
        assert "2026-11-18" in context_prompt()
        assert "observed" not in json.dumps(turn_metadata())
    finally:
        TURN_PAGE_CONTEXT.reset(token)


def test_large_context_does_not_truncate_into_untrusted_instructions(monkeypatch):
    from src.core import assistant_page_context

    cfg = dict(assistant_page_context.context_config())
    cfg["max_chars"] = 50
    monkeypatch.setattr(assistant_page_context, "context_config", lambda: cfg)
    token = TURN_PAGE_CONTEXT.set({"enabled": True, "sources": [{"data": "x" * 1000}]})
    try:
        assert "x" * 100 not in context_prompt()
        assert "bounded" in context_prompt()
    finally:
        TURN_PAGE_CONTEXT.reset(token)


def test_scope_change_resets_chat_session_and_cli_history():
    from src.frontend.common.assistant_context import ContextTurns

    captured = []
    selected = {"view": "stock", "enabled": False, "sources": []}

    def chat(session, message, history, *args):
        captured.append((session, list(history)))
        yield 8, [], "", [], "done"

    def cli(message, history, backend):
        captured.append((backend, list(history)))
        yield [], "", "done"

    turns = ContextTurns(lambda *args: dict(selected), chat, cli)
    state = {}
    list(turns.send(4, "q", [{"content": "old"}], "api", [], "", "", "read-only", True, state))
    assert captured[-1] == (0, [])
    list(turns.send(8, "q", [{"content": "current"}], "api", [], "", "", "read-only", True, state))
    assert captured[-1][0] == 8 and captured[-1][1]
    selected["view"] = "macro"
    list(turns.send(8, "q", [{"content": "stale"}], "api", [], "", "", "read-only", True, state))
    assert captured[-1] == (0, [])
    list(turns.cli_send("q", [{"content": "stale"}], "codex", True, state))
    assert captured[-1] == ("codex", [])


def test_legacy_cli_assistant_receives_same_page_envelope(client, monkeypatch):
    from src.frontend.service import assistant
    from src.strategy.codex_cli import CodexStreamEvent

    seen = []

    class Cli:
        display_name = "Declared CLI"

        def stream(self, prompt, **kwargs):
            seen.append(prompt)
            yield CodexStreamEvent("message", "completed", "Declared reply")

    monkeypatch.setattr(assistant, "CodexCliRunner", Cli)
    token = TURN_PAGE_CONTEXT.set(
        {"enabled": True, "module": "market", "view": "stock", "sources": [{"id": "P1", "data": stock()}]}
    )
    try:
        result = list(assistant._codex_chat_events("What is this ratio?", [], "codex"))
    finally:
        TURN_PAGE_CONTEXT.reset(token)
    assert "123.45" in seen[0] and "P1" in seen[0]
    assert result[-1][0][0]["content"] == "What is this ratio?"
