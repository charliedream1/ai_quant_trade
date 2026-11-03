"""Visible Gradio operations; model is an explicit protocol double, not a real acceptance claim."""

import argparse
import json
import re
from pathlib import Path
from time import perf_counter

import yaml
from graph_browser_support import GraphBrowser
from loguru import logger
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import navigate


def main(base: str, runtime: Path, output: Path):
    cfg = yaml.safe_load(Path("egs/strategy_components.yaml").read_text(encoding="utf-8"))
    seed = json.loads((runtime / "browser.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1050})
        audit = GraphBrowser(page, {"base_url": base}, output)
        audit.start()

        def execute(name):
            audit.preset("Agent方案 / " + name)
            frame = audit.frame
            expect(audit.node("analysis")).to_be_visible()
            expect(audit.node("decision")).to_be_visible()
            audit.node("decision").click()
            expect(frame.locator(".graph-properties")).to_contain_text("研究方案")
            audit.textbox(cfg["ui"]["symbols"]).fill(",".join(seed["history"]))
            audit.dropdown(cfg["ui"]["mode"], "纯量化回测")
            accordion = frame.get_by_text("日期、模型与模拟账户", exact=True)
            if not audit.textbox(cfg["ui"]["start"]).is_visible():
                accordion.click()
            audit.textbox(cfg["ui"]["start"]).fill(seed["days"][40])
            audit.textbox(cfg["ui"]["end"]).fill(seed["days"][48])
            audit.textbox("行情快照ID（可选；重用已归档真实行情）").fill(seed["snapshot_id"])
            frame.get_by_role("spinbutton", name=cfg["ui"]["model_id"], exact=True).fill("1")
            panel = frame.get_by_text("Agent策略设置（中文多空 / 双团队竞赛）", exact=True)
            if not frame.locator("#agent-strategy-documents input").is_visible():
                panel.click()
            frame.locator("#agent-strategy-documents input").fill(str(seed["documents_id"]))
            roles = frame.locator("#agent-strategy-role-models textarea")
            if not roles.is_visible():
                frame.get_by_text("按角色指定模型（可选）", exact=True).click()
            roles.fill("technical: {model_id: 1, reasoning_effort: low}" if name == "中文事件确认" else "{}")
            frame.get_by_text("按角色指定模型（可选）", exact=True).click()
            audit.dropdown("Agent执行模式", "历史模型研究（非当时决定回放）")
            frame.locator("#agent-strategy-mode input").press("Tab")
            frame.locator("#pipeline-preset").scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            zoom = frame.locator(".svelte-flow__controls-zoomin")
            if zoom.count():
                zoom.click(click_count=2, delay=150)
                page.wait_for_timeout(300)
            page.screenshot(
                path=str(output / ("79-agent-workshop.jpg" if name == "中文事件确认" else "81-agent-contest.jpg")),
                type="jpeg",
                quality=88,
            )
            started = perf_counter()
            previous_run = audit.textbox("运行ID").input_value()
            audit.button(cfg["ui"]["run"]).click()
            expect(audit.textbox("运行ID")).not_to_have_value(previous_run, timeout=30000)
            expect(audit.textbox(cfg["ui"]["status"])).to_have_value(re.compile("完成|finished"), timeout=90000)
            run_id = audit.textbox("运行ID").input_value()
            run = audit.api("/strategy-pipeline-runs/" + run_id)
            assert run["status"] == "finished", run.get("result")
            assert not run["result"]["decision_errors"], run["result"]["decision_errors"]
            assert run["result"]["agent_model_budget"]["used"] > 0
            assert run["result"]["agent_validation_mode"] == "research"
            expected_component = "cn_debate" if name == "中文事件确认" else "contest_research"
            assert any(row["component"] == expected_component for row in run["result"]["diagnostics"]["stages"])
            if name == "竞赛事件延续":
                assert run["result"]["metrics"]["trade_count"] == 0
            audit.run_ids.append(run_id)
            audit.node("decision").click()
            audit.button("查看当前步骤").click()
            expect(frame.locator(".graph-properties")).to_contain_text("agent_strategy", timeout=15000)
            frame.locator(".node-evidence").scroll_into_view_if_needed()
            page.wait_for_timeout(150)
            page.screenshot(
                path=str(
                    output / ("80-agent-process.jpg" if name == "中文事件确认" else "81-agent-contest-result.jpg")
                ),
                type="jpeg",
                quality=88,
            )
            return {
                "run_id": run_id,
                "seconds": round(perf_counter() - started, 3),
                "metrics": run["result"]["metrics"],
                "calls": run["result"]["agent_model_budget"],
                "model_scope": "explicit_protocol_double",
            }

        audit.scenario("debate", lambda: execute("中文事件确认"))
        audit.scenario("contest", lambda: execute("竞赛事件延续"))

        def cancel():
            audit.preset("Agent方案 / 中文事件确认")
            old = audit.textbox("运行ID").input_value()
            audit.button(cfg["ui"]["run"]).click()
            expect(audit.textbox("运行ID")).not_to_have_value(old, timeout=30000)
            run_id = audit.textbox("运行ID").input_value()
            audit.button(cfg["ui"]["cancel"]).click()
            expect(audit.textbox(cfg["ui"]["status"])).to_have_value(re.compile("取消"), timeout=30000)
            run = audit.api("/strategy-pipeline-runs/" + run_id)
            deadline = perf_counter() + 15
            while run["status"] == "cancelling" and perf_counter() < deadline:
                page.wait_for_timeout(100)
                run = audit.api("/strategy-pipeline-runs/" + run_id)
            assert run["status"] == "cancelled", run["status"]
            return {"run_id": run_id, "cancelled": True}

        audit.scenario("cancel", cancel)

        def reports():
            frame = navigate(page, "knowledge", "reports")
            expect(frame.locator("#report-source")).to_be_visible(timeout=60000)
            # Wait for the cold module's initial route before interacting with its controls.
            destination = page.locator("[data-workspace-view-module='knowledge'][data-workspace-view='reports']")
            expect(destination).to_have_class(re.compile("active"), timeout=30000)
            expect(frame.locator("#report-selected")).to_be_visible(timeout=30000)
            frame.locator("#report-source input").click()
            frame.get_by_role("option", name="Agent策略", exact=True).click()
            frame.get_by_role("button", name="刷新报告库", exact=True).click()
            frame.locator("#report-selected input").click()
            frame.get_by_role("option").filter(has_text="竞赛事件延续").first.click()
            frame.get_by_role("button", name="打开报告", exact=True).click()
            expect(
                frame.frame_locator('iframe[title="Agent策略报告"]').get_by_role(
                    "heading", name="竞赛事件延续", exact=True
                )
            ).to_be_visible(timeout=30000)
            frame.locator('iframe[title="Agent策略报告"]').scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            page.screenshot(path=str(output / "82-agent-report.jpg"), type="jpeg", quality=88)
            return {"report_library": True}

        audit.scenario("reports", reports)

        def dark():
            navigate(page, "strategy", "workshop")
            page.locator("#app-theme-toggle").click()
            expect(page.locator("#app-theme-label")).to_have_text("深色")
            audit.node("decision").scroll_into_view_if_needed()
            page.wait_for_timeout(350)
            page.screenshot(path=str(output / "83-agent-dark.jpg"), type="jpeg", quality=88)
            page.locator("#app-theme-toggle").click()
            return {"dark": True}

        audit.scenario("dark", dark)
        audit.flush()
        browser.close()
        assert all(row["passed"] for row in audit.results), audit.results
        assert not [row for row in audit.errors if row["kind"] == "pageerror"], audit.errors
        logger.info("Agent browser acceptance passed; model calls use only the explicit fixture")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base, args.runtime, args.output)
