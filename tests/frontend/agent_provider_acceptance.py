"""Browser clicks verify lazy research controls without paid model requests."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from loguru import logger
from playwright.sync_api import expect, sync_playwright


def main(base: str, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1580, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            started = perf_counter()
            page.goto(base + "/app/?module=strategy&view=alpha")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#alpha-backend input")).to_be_visible(timeout=90000)
            close = page.locator("#notification-toasts button")
            if close.count():
                close.first.click()
            results.append({"alpha_ready_seconds": round(perf_counter() - started, 3)})
            frame.locator("#alpha-backend input").click()
            frame.get_by_role("option", name="Qoder CLI", exact=True).click()
            frame.locator("#alpha-cli-model textarea").fill("auto")
            expect(frame.locator("#alpha-backend input")).to_have_value("Qoder CLI")
            frame.locator("#alpha-cli-model textarea").press("Tab")
            page.wait_for_timeout(300)
            page.screenshot(path=str(output / "92-agent-provider-alpha.jpg"), type="jpeg", quality=85)
            results.append({"alpha_backend_selection": "qoder", "model": "auto", "model_called": False})

            started = perf_counter()
            page.goto(base + "/app/?module=ai&view=workflow")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.get_by_role("tab", name="专家团", exact=True)).to_be_attached(timeout=90000)
            results.append({"workbench_ready_seconds": round(perf_counter() - started, 3)})
            # The existing workbench keeps deeper settings under its advanced panels.
            target = frame.locator("#research-team-backend input")
            for title in ["专家与团队", "专家团", "多Agent回测复核"]:
                candidates = frame.get_by_text(title, exact=True)
                if candidates.count() and candidates.first.is_visible():
                    candidates.first.click()
            if not target.is_visible():
                # Reveal the real parent tabs in the same Gradio document.
                tab = frame.get_by_role("tab", name="专家团", exact=True)
                if tab.count():
                    tab.click(force=True)
            expect(target).to_be_visible(timeout=15000)
            target.click()
            frame.get_by_role("option", name="Codex CLI", exact=True).click()
            expect(target).to_have_value("Codex CLI")
            target.press("Tab")
            page.wait_for_timeout(300)
            target.scroll_into_view_if_needed()
            page.screenshot(path=str(output / "93-agent-provider-team.jpg"), type="jpeg", quality=85)
            results.append({"team_backend_selection": "codex", "model_called": False})
            assert not errors, errors
        finally:
            (output / "browser.json").write_text(
                json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            browser.close()
    logger.info("Agent provider browser acceptance passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.output)
