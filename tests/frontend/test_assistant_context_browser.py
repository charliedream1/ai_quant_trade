"""Rendered page evidence reaches actual API/CLI adapters and stays outside visible questions."""

from types import SimpleNamespace

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("backend", ["api", "cli"])
def test_loaded_page_prompt_preview_and_context_off(cli_command, client, monkeypatch, tmp_path, backend):
    from src.agent import workspace_backend
    from src.agent.model_catalog import create_model
    from src.core.repository import Repository
    from src.strategy.codex_cli import CodexStreamEvent

    create_model(
        {
            "name": "Declared context acceptance",
            "model_name": "declared-context",
            "base_url": "http://127.0.0.1:9",
            "level": "fast",
        }
    )
    seen = []

    def answer(prompt):
        seen.append(prompt)
        return "Declared page-scoped answer" if "P1" in prompt else "Declared answer without page data"

    class Agent:
        def __init__(self, **kwargs):
            pass

        def run_once(self, prompt, **kwargs):
            return SimpleNamespace(
                text=answer(prompt), model="declared-context", tool_events=[], needs_user=False, duration_ms=1, turns=1
            )

    class Cli:
        def __init__(self, **kwargs):
            pass

        def stream(self, prompt, **kwargs):
            yield CodexStreamEvent("message", "completed", answer(prompt))

    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "1")
    monkeypatch.setattr(workspace_backend, "GenericAgentRuntime", Agent)
    monkeypatch.setattr(workspace_backend, "CodexCliRunner", Cli)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        try:
            page.goto(cli_command.base_url + "/app/?module=market&view=quotes", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#ai-floating-button")).to_have_attribute("data-drag-ready", "1", timeout=90000)
            frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]').click()
            expect(frame.locator("#market-sectors-plot .js-plotly-plot")).to_be_visible(timeout=60000)
            frame.locator("#ai-floating-button").click()
            panel = frame.locator("#ai-floating-panel")
            panel.locator("#assistant-context-preview").click()
            expect(panel.locator("#assistant-context-scope")).to_contain_text("market/quotes")
            if backend == "cli":
                panel.locator("#ai-chat-backend input").click()
                panel.get_by_role("option", name="Codex CLI", exact=True).click()
                expect(panel.locator("#ai-chat-send")).to_be_enabled(timeout=20000)
            field = panel.locator("#ai-chat-input textarea")
            field.fill("Explain the current board")
            panel.locator("#ai-chat-send").click()
            expect(panel.locator("#ai-chat-history")).to_contain_text("Declared page-scoped answer", timeout=30000)
            assert '"view": "quotes"' in seen[-1] and '"change_pct"' in seen[-1] and '"board": "industry"' in seen[-1]
            record = Repository().db.query_one(
                "SELECT content,metadata FROM ai_workspace_messages WHERE role='user' ORDER BY id DESC LIMIT 1"
            )
            assert record["content"] == "Explain the current board"
            assert '"page_context"' in record["metadata"]
            panel.locator("#assistant-use-page input").uncheck()
            field.fill("Explain without page context")
            panel.locator("#ai-chat-send").click()
            expect(panel.locator("#ai-chat-history")).to_contain_text(
                "Declared answer without page data", timeout=30000
            )
            assert "Current-page context" not in seen[-1]
            page.screenshot(path=str(tmp_path / (backend + "-page-context.png")), full_page=True)
        finally:
            browser.close()
