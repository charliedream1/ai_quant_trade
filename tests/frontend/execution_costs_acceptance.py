"""Visible form submission verifies the exact run cost snapshot in all three entrances."""

import argparse
import json
import re
from pathlib import Path
from uuid import uuid4

import requests
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate

from src.strategy.composition.config import template


def field(frame, label):
    return frame.get_by_label(label, exact=True).filter(visible=True)


def choose(frame, label, option):
    field(frame, label).click()
    frame.get_by_role("option", name=option, exact=True).filter(visible=True).click()


def costs(frame, minimum):
    frame.get_by_text("交易成本与执行假设", exact=True).filter(visible=True).click()
    choose(frame, "费用方案", "沪深A股成本示例（核对券商费率）")
    field(frame, "买入佣金（%）").fill("0.04")
    field(frame, "每外部订单最低佣金（元）").fill(str(minimum))
    frame.get_by_role("button", name="预览实际执行配置", exact=True).filter(visible=True).click()
    expect(frame.get_by_text("已解析本次执行配置", exact=False).filter(visible=True)).to_be_visible(timeout=30000)


def post(base, path, data):
    result = requests.post(base + "/api/v1" + path, json=data, timeout=60).json()
    assert result["code"] == 0, result
    return result["data"]


def run(base, output):
    output.mkdir(parents=True, exist_ok=True)
    strategy = post(
        base,
        "/strategy-examples/import",
        {
            "example": "egs/strategy_examples/standard_port_strategy.py",
            "name": "cost-ui-" + uuid4().hex[:8],
            "default_params": {"min_change_pct": 0, "quantity": 100},
        },
    )
    definition = template("rule_trend")
    definition.update(name="cost-graph-" + uuid4().hex[:8], nodes=[], output="universe")
    definition["universe"]["symbols"] = ["000001"]
    definition["execution"]["initial_capital"] = 10000
    draft = post(base, "/strategy-pipelines", {"definition": definition})
    version = post(base, f"/strategy-pipelines/{draft['id']}/publish", {})
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(base + "/app/?module=simulation&view=backtest")
            frame = active(page)
            expect(field(frame, "策略 ID")).to_be_visible(timeout=90000)
            field(frame, "策略 ID").fill(str(strategy["id"]))
            field(frame, "标的代码").fill("000001")
            field(frame, "开始日期").fill("2026-01-05")
            field(frame, "结束日期").fill("2026-01-16")
            costs(frame, 3)
            field(frame, "费用方案").evaluate("el => el.scrollIntoView({block: 'start'})")
            page.screenshot(path=str(output / "01-regular-cost-settings.jpg"), type="jpeg", quality=88)
            frame.get_by_role("button", name="开始回测", exact=True).click()
            expect(field(frame, "任务 ID")).to_have_value(re.compile(r"^[1-9][0-9]*$"), timeout=90000)
            task_id = int(field(frame, "任务 ID").input_value())
            task = requests.get(base + f"/api/v1/backtests/{task_id}", timeout=30).json()["data"]
            policy = task["parameter_snapshot"]["run"]["execution_costs"]
            assert policy["minimum_commission"] == 3 and policy["buy_commission_rate"] == 0.0004
            results["regular"] = task
            frame.get_by_text("实际执行成本", exact=True).filter(visible=True).evaluate(
                "el => el.scrollIntoView({block: 'center'})"
            )
            page.screenshot(path=str(output / "02-regular-cost-results.jpg"), type="jpeg", quality=88)

            frame = navigate(page, "strategy", "management")
            expect(frame.get_by_role("tab", name="策略库", exact=True)).to_be_visible(timeout=90000)
            frame.get_by_role("tab", name="策略库", exact=True).click()
            field(frame, "策略 ID").fill(str(strategy["id"]))
            field(frame, "回测标的").fill("000001")
            field(frame, "开始日期").fill("2026-01-05")
            field(frame, "结束日期").fill("2026-01-16")
            costs(frame, 4)
            frame.get_by_role("button", name="策略一键回测", exact=True).click()
            expect(field(frame, "回测任务 ID（可恢复）")).to_have_value(re.compile(r"^[1-9][0-9]*$"), timeout=30000)
            task_id = int(field(frame, "回测任务 ID（可恢复）").input_value())
            expect(frame.get_by_text("实际执行成本", exact=True).filter(visible=True)).to_be_visible(timeout=90000)
            task = requests.get(base + f"/api/v1/backtests/{task_id}", timeout=30).json()["data"]
            assert task["parameter_snapshot"]["run"]["execution_costs"]["minimum_commission"] == 4
            results["quick"] = task
            frame.get_by_text("实际执行成本", exact=True).filter(visible=True).evaluate(
                "el => el.scrollIntoView({block: 'center'})"
            )
            page.screenshot(path=str(output / "03-quick-costs.jpg"), type="jpeg", quality=88)

            page.goto(base + f"/app/?module=strategy&view=workshop&pipeline_version={version['id']}")
            frame = active(page)
            expect(frame.locator("#strategy-graph-editor")).to_be_visible(timeout=90000)
            expect(field(frame, "预置方案")).to_have_value(re.compile("已发布 /"), timeout=30000)
            choose(frame, "运行模式", "纯量化回测")
            frame.get_by_text("日期、模型与模拟账户", exact=True).filter(visible=True).click()
            field(frame, "开始日期").fill("2026-01-05")
            field(frame, "截止日期（留空为今天）").fill("2026-01-16")
            costs(frame, 6)
            frame.get_by_role("button", name="执行当前方案", exact=True).click()
            expect(field(frame, "实际运行状态")).to_have_value(re.compile("已完成"), timeout=120000)
            run_id = field(frame, "运行ID").input_value()
            result = requests.get(base + f"/api/v1/strategy-pipeline-runs/{run_id}", timeout=30).json()["data"]
            assert result["result"]["metrics"]["execution_costs"]["minimum_commission"] == 6
            assert result["version_id"] == version["id"]
            results["graph"] = result
            field(frame, "费用方案").evaluate("el => el.scrollIntoView({block: 'start'})")
            page.screenshot(path=str(output / "04-graph-execution-costs.jpg"), type="jpeg", quality=88)
            assert not errors, errors
        finally:
            results["page_errors"] = errors
            (output / "browser-results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            page.screenshot(path=str(output / "browser-last.jpg"), type="jpeg", quality=88)
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.base_url, args.output)
