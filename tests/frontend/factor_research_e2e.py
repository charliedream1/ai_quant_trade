"""Opt-in browser acceptance for independently implemented factor workflows."""

import argparse
from pathlib import Path

import yaml
from graph_browser_support import GraphBrowser
from loguru import logger
from playwright.sync_api import expect, sync_playwright

from src.core.config import PROJECT_ROOT


def workflow(browser: GraphBrowser, name: str, node: str, kind: str):
    browser.preset(name)
    row = browser.run_ui()
    result = row["result"]
    assert result["trades"] and not result["decision_errors"]
    browser.button("全屏画布").click()
    browser.button("查看全图").click()
    browser.node(node).click()
    if kind == "model":
        models = result["diagnostics"]["model_diagnostics"]
        assert all(model["fits"] and model["predictions"] for model in models.values())
        assert {model["fits"][-1]["feature_set"] for model in models.values()} == {"trend", "defensive", "balanced"}
        expect(browser.frame.locator(".graph-properties")).to_contain_text("模型特征集")
    else:
        expect(browser.frame.locator(".factor-evidence")).to_be_visible()
        if kind == "research":
            expect(browser.frame.locator(".factor-evidence table")).to_contain_text("RankIC")
        else:
            expect(browser.frame.locator(".factor-evidence progress").first).to_be_visible()
    consistency = browser.cli_replay(row, "cli-" + kind + ".json")
    if browser.frame.locator(".graph-palette").is_visible():
        browser.button("添加组件").click()
    browser.button("查看全图").click()
    if kind != "model":
        browser.frame.locator(".factor-evidence").scroll_into_view_if_needed()
    return {
        "run_id": row["id"],
        "trade_count": result["metrics"]["trade_count"],
        "source": result["source"],
        "duration_ms": result["duration_ms"],
        "consistency": consistency,
    }


def dark_research(browser: GraphBrowser):
    before = {row["id"] for row in browser.api("/strategy-pipeline-runs")}
    run_id = browser.results[1]["detail"]["run_id"]
    browser.preset("滚动有效性多因子")
    browser.textbox("运行ID").fill(run_id)
    browser.button("查看当前步骤").click()
    expect(browser.frame.locator(".graph-footer")).to_contain_text(run_id)
    browser.page.locator("#app-theme-toggle").click()
    expect(browser.page.locator("html")).to_have_attribute("data-theme", "dark")
    browser.button("全屏画布").click()
    browser.node("research").click()
    browser.frame.locator(".factor-evidence").scroll_into_view_if_needed()
    expect(browser.frame.locator(".factor-evidence table")).to_contain_text("RankIC")
    assert before == {row["id"] for row in browser.api("/strategy-pipeline-runs")}
    return {"run_id": run_id, "dark": True, "new_runs_created": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--inspect-run")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    output = (PROJECT_ROOT / args.output).resolve()
    if not output.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Browser artifacts must stay inside this project")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
            page.set_default_timeout(30_000)
            audit = GraphBrowser(page, cfg, output)
            audit.start()
            if args.inspect_run:
                page.wait_for_load_state("networkidle")
                audit.save(
                    "initial-network.json",
                    {"console": audit.errors, "same_origin": audit.http_errors, "external": audit.external_http_errors},
                )
                response = audit.session.get(
                    audit.base + "/api/v1/strategy-pipeline-runs/" + args.inspect_run + "/files/report.html", timeout=30
                )
                response.raise_for_status()
                page.set_content(response.text, wait_until="networkidle")
                audit.save(
                    "report-network.json",
                    {"console": audit.errors, "same_origin": audit.http_errors, "external": audit.external_http_errors},
                )
                return 0
            audit.scenario("01-factor-equal", lambda: workflow(audit, "标准化量价多因子", "scores", "score"))
            audit.scenario("02-factor-research", lambda: workflow(audit, "滚动有效性多因子", "research", "research"))
            audit.scenario("03-feature-groups", lambda: workflow(audit, "多特征组模型组合", "trend_model", "model"))
            audit.scenario("04-dark-research", lambda: dark_research(audit))
            audit.flush()
            failed = [row for row in audit.results if not row["passed"]]
            errors = [row for row in audit.errors if row["kind"] in {"error", "pageerror"}]
            logger.info(
                "Browser acceptance: passed={} failed={} errors={} HTTP={}",
                len(audit.results) - len(failed),
                len(failed),
                errors,
                audit.http_errors,
            )
            return int(bool(failed or errors or audit.http_errors))
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
