"""Actual composer switching preserves provider identity and visible billing metadata."""

from threading import Event

import pytest
from playwright.sync_api import expect, sync_playwright

from src.frontend.common import composer_catalog


@pytest.mark.parametrize("prefix", ["ai-console", "ai-chat"])
def test_switch_refresh_billing_and_delayed_provider(cli_command, monkeypatch, tmp_path, prefix):
    started, release = Event(), Event()
    calls = []

    def discover(backend, refresh):
        calls.append((backend, refresh))
        if backend == "qoder":
            started.set()
            assert release.wait(15)
        return {
            "backend": backend,
            "status": "ready",
            "source": "Declared acceptance catalogue",
            "updated": "2026-11-16T00:00:00Z",
            "rows": [
                {
                    "id": backend + "-one",
                    "name": backend + " available",
                    "billing": "Free (reported by provider)" if backend == "codebuddy" else "1.2× credits",
                    "efforts": ["low"],
                }
            ],
        }

    monkeypatch.setattr(composer_catalog, "discover", discover)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1100})
            route = "/app/?module=ai&view=workbench" if prefix == "ai-console" else "/app/?module=market&view=quotes"
            page.goto(cli_command.base_url + route, wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(
                frame.locator("#ai-console-input textarea" if prefix == "ai-console" else "#market-quotes-refresh")
            ).to_be_visible(timeout=90000)
            if prefix == "ai-chat":
                frame.locator('#ai-floating-button[data-drag-ready="1"]').click()

            def choose(field, label):
                frame.locator(f"#{prefix}-{field} input").click()
                frame.locator(f"#{prefix}-{field} input").fill(label.split(" · ")[0] if field == "model" else "")
                frame.get_by_role("option", name=label, exact=True).click()

            choose("backend", "Qoder CLI")
            assert started.wait(5)
            choose("backend", "CodeBuddy Code")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("Available models loaded", timeout=10000)
            release.set()
            choose("model", "codebuddy available · Free (reported by provider)")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("Free (reported by provider)")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("Declared acceptance catalogue")
            frame.locator(f"#{prefix}-refresh-models").click()
            expect(frame.locator(f"#{prefix}-model input")).to_have_value(
                "codebuddy available · Free (reported by provider)"
            )
            choose("backend", "Codex CLI")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("Codex CLI · Billing:")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("Available models loaded")
            choose("model", "codex available · 1.2× credits")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("1.2× credits")
            choose("reasoning", "低")
            choose("backend", "WorkBuddy（未接入）")
            expect(frame.locator(f"#{prefix}-billing")).to_contain_text("chat is unavailable")
            expect(frame.locator(f"#{prefix}-send")).to_be_disabled()
            page.screenshot(path=str(tmp_path / (prefix + "-billing.png")), full_page=True)
            assert ("codebuddy", True) in calls
        except Exception:
            page.screenshot(path=str(tmp_path / "failed.png"), full_page=True)
            (tmp_path / "options.txt").write_text(
                str(frame.get_by_role("option").all_text_contents()), encoding="utf-8"
            )
            raise
        finally:
            release.set()
            browser.close()
