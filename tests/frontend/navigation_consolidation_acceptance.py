"""Visible navigation, shared forms and task identity against an isolated running service."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import requests
from graph_browser_support import GraphBrowser
from loguru import logger
from playwright.sync_api import expect, sync_playwright
from workspace_revision_acceptance import active, navigate


def field(frame, label):
    return frame.get_by_label(label, exact=True).filter(visible=True)


def dropdown(frame, label, option):
    field(frame, label).click()
    frame.get_by_role("option", name=option, exact=True).filter(visible=True).click()


def post(base, path, data):
    result = requests.post(base + "/api/v1" + path, json=data, timeout=60).json()
    assert result["code"] == 0, result
    return result["data"]


def alias_and_rag(page, base, output):
    page.goto(base + "/app/?module=research&view=papers")
    frame = active(page)
    expect(frame.get_by_role("tab", name="论文检索", exact=True)).to_have_attribute(
        "aria-selected", "true", timeout=90000
    )
    assert page.locator("[data-workspace-module]").count() == 9
    page.screenshot(path=str(output / "01-merged-library.jpg"), type="jpeg", quality=88)
    note = post(
        base,
        "/kb/notes",
        {"title": "Navigation RAG fixture", "content": "回撤表示净值相对历史峰值的下降；费用会减少净收益。"},
    )
    frame = navigate(page, "knowledge", "qa")
    layout = frame.locator("#rag-chat-layout")
    field(layout, "问题").fill("回撤")
    layout.get_by_role("button", name="提问", exact=True).click()
    expect(layout.locator("#rag-chat-references")).to_contain_text("Navigation RAG fixture", timeout=60000)
    session = field(layout, "会话 ID").input_value()
    navigate(page, "knowledge", "library")
    frame = navigate(page, "knowledge", "qa")
    assert field(frame, "会话 ID").input_value() == session
    page.screenshot(path=str(output / "02-shared-rag.jpg"), type="jpeg", quality=88)
    return {"note_id": note["doc_id"], "session": session, "legacy_papers": True, "visible_modules": 9}


def factor_and_etf(page, base, output):
    page.goto(base + "/app/?module=market&view=factors")
    frame = active(page)
    expect(field(frame, "监控范围")).to_be_visible(timeout=90000)
    dropdown(frame, "监控范围", "自定义股票池")
    field(frame, "自定义股票代码（仅自定义范围使用）").fill("600519,300750,000001,688981,300124")
    dropdown(frame, "分析后端", "Qlib信号分析")
    frame.get_by_role("button", name="运行因子监控", exact=True).click()
    frame.get_by_text("有效性、覆盖与原始截面", exact=True).filter(visible=True).click()
    expect(frame.get_by_text("Qlib信号分析：可用", exact=False).filter(visible=True)).to_be_visible(timeout=90000)
    field(frame, "监控范围").scroll_into_view_if_needed()
    page.screenshot(path=str(output / "03-unified-factor.jpg"), type="jpeg", quality=88)
    frame = navigate(page, "strategy", "etf")
    expect(field(frame, "ETF池")).to_be_visible(timeout=60000)
    expect(frame.get_by_text("mock", exact=False).filter(visible=True).first).to_be_visible(timeout=60000)
    page.screenshot(path=str(output / "04-etf-navigation.jpg"), type="jpeg", quality=88)
    return {"legacy_factor": True, "qlib_available": True, "etf_navigation": True}


def graph(page, base, output):
    frame = navigate(page, "strategy", "workshop")
    expect(frame.locator(".strategy-graph-app")).to_be_visible(timeout=90000)
    helper = GraphBrowser(page, {"base_url": base}, output)
    helper.preset("规则趋势基础")
    node = helper.node("trend")
    node.click()
    expect(frame.locator(".graph-properties")).to_contain_text("短窗口")
    prior = node.get_attribute("style")
    box = node.bounding_box()
    assert box
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 18)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] / 2 + 60, box["y"] + 48, steps=12)
    page.mouse.up()
    expect(node).not_to_have_attribute("style", prior)
    frame.get_by_role("button", name="全屏画布", exact=True).click()
    page.screenshot(path=str(output / "05-graph-entry.jpg"), type="jpeg", quality=88)
    frame.get_by_role("button", name="退出全屏", exact=True).click()
    return {"dragged_node": "trend", "properties": True, "fullscreen": True}


def quick_configuration(page, output):
    frame = navigate(page, "ai", "main")
    expect(frame.locator("#ai-console-input textarea")).to_be_visible(timeout=90000)
    frame.get_by_role("button", name="⌁ MCP 服务", exact=True).click()
    frame.get_by_role("link", name="新增或编辑MCP服务", exact=True).click()
    frame = active(page)
    expect(frame.get_by_role("tab", name="MCP 服务", exact=True)).to_have_attribute(
        "aria-selected", "true", timeout=60000
    )
    page.screenshot(path=str(output / "06-shared-configuration.jpg"), type="jpeg", quality=88)
    frame = navigate(page, "ai", "main")
    frame.get_by_role("button", name="◇ Skill", exact=True).click()
    frame.get_by_role("link", name="登记或配置Skill", exact=True).click()
    frame = active(page)
    expect(frame.get_by_role("tab", name="Skill 配置", exact=True)).to_have_attribute(
        "aria-selected", "true", timeout=60000
    )
    return {"mcp_settings": True, "skill_settings": True, "ai_context_retained": True}


def task_context(page, base, output):
    results = json.loads((output.parent / "browser-costs/browser-results.json").read_text(encoding="utf-8"))
    task_id = results["quick"]["id"]
    page.goto(base + f"/app/?module=simulation&view=backtest&task_id={task_id}")
    frame = active(page)
    expect(frame.locator("#route-backtest-task-id input")).to_have_value(str(task_id), timeout=90000)
    expect(frame.get_by_text("实际执行成本", exact=True).filter(visible=True)).to_be_visible(timeout=60000)
    frame.get_by_text("实际执行成本", exact=True).filter(visible=True).scroll_into_view_if_needed()
    page.screenshot(path=str(output / "07-shared-task-results.jpg"), type="jpeg", quality=88)
    frame = navigate(page, "live", "attribution")
    frame.get_by_role("link", name="打开实盘运行归因", exact=True).click()
    frame = active(page)
    expect(frame.get_by_text("分析来源", exact=True)).to_be_visible(timeout=60000)
    expect(frame.get_by_role("radio", name="真实交易观测闭环", exact=True)).to_be_checked(timeout=30000)
    page.screenshot(path=str(output / "08-shared-analysis.jpg"), type="jpeg", quality=88)
    return {"task_id": task_id, "auto_opened": True, "live_analysis_context": True}


def run(base, output):
    output.mkdir(parents=True, exist_ok=True)
    results, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            for name, action in [
                ("library", lambda: alias_and_rag(page, base, output)),
                ("factors", lambda: factor_and_etf(page, base, output)),
                ("graph", lambda: graph(page, base, output)),
                ("configuration", lambda: quick_configuration(page, output)),
                ("task_context", lambda: task_context(page, base, output)),
            ]:
                started = perf_counter()
                results[name] = {"detail": action(), "seconds": round(perf_counter() - started, 3)}
                logger.info("Navigation browser {} passed", name)
            page.locator("#app-theme-toggle").click()
            expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.screenshot(path=str(output / "09-dark-navigation.jpg"), type="jpeg", quality=88)
            page.locator("#workspace-sidebar-toggle").click()
            assert page.locator(".sidebar-collapsed").count() == 1
            results["appearance"] = {
                "dark": True,
                "collapsed": True,
                "cache_frames": page.locator("iframe.workspace-frame").count(),
            }
            assert results["appearance"]["cache_frames"] <= 3
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
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.base_url, args.output)
