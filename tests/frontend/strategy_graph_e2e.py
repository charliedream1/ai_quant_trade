"""Opt-in end-to-end graph audit against an isolated real-data Gradio service."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml
from graph_browser_support import GraphBrowser
from loguru import logger
from playwright.sync_api import expect, sync_playwright

from src.core.config import PROJECT_ROOT
from src.strategy.composition.config import templates
from src.strategy.composition.validation import compile_plan, digest


def templates_ui(a):
    rows = []
    for item in templates():
        a.preset(item["definition"]["name"])
        actual = a.compiled_digest()
        assert actual == digest(compile_plan(item["definition"]))
        rows.append({"id": item["id"], "nodes": a.nodes().count(), "digest": actual})
    return rows


def file_roundtrip(a):
    a.preset("规则趋势基础")
    a.edit_number("trend", "短窗口", "8")
    with a.page.expect_download() as pending:
        a.button("导出方案").click()
    downloaded = a.output / "browser-export.json"
    pending.value.save_as(downloaded)
    exported = json.loads(downloaded.read_text(encoding="utf-8"))
    assert exported["document"]["nodes"][1]["params"]["short"] == 8
    a.preset("ETF多资产配置")
    with a.page.expect_file_chooser() as pending_file:
        a.frame.locator(".graph-import").click()
    pending_file.value.set_files(downloaded)
    expect(a.frame.locator(".graph-breadcrumb")).to_contain_text("规则趋势基础")
    a.apply()
    assert a.definition()["nodes"][1]["params"]["short"] == 8
    return {"download": downloaded.name, "imported_parameters": {"short": 8}, "format": exported["format"]}


def edit_and_wire(a):
    a.preset("规则趋势基础")
    before = a.compiled_digest()
    a.button("全屏画布").click()
    a.node("trend").click()
    a.button("rules ↗").click()
    a.button("trend ↖").click()
    a.edit_number("trend", "短窗口", "7")
    expect(a.button("撤销")).to_be_enabled()
    a.button("撤销").click()
    expect(a.frame.get_by_role("spinbutton", name="短窗口", exact=True)).to_have_value("5")
    a.button("重做").click()
    expect(a.frame.get_by_role("spinbutton", name="短窗口", exact=True)).to_have_value("7")
    edge = a.frame.locator('.svelte-flow__edge[data-id="eligibility>trend"] .svelte-flow__edge-path')
    edge.click(force=True)
    a.button("移除此计算连线").click()
    expect(a.frame.locator('.svelte-flow__edge[data-id="eligibility>trend"]')).to_have_count(0)
    a.drag(a.node("eligibility").locator(".source"), a.node("trend").locator(".target"))
    expect(a.frame.locator('.svelte-flow__edge[data-id="eligibility>trend"]')).to_have_count(1)
    a.node("trend").click()
    a.button("复制阶段").click()
    expect(a.nodes()).to_have_count(10)
    a.button("移除阶段").click()
    expect(a.nodes()).to_have_count(9)
    a.apply()
    assert a.definition()["nodes"][1]["params"]["short"] == 7
    assert a.compiled_digest() != before
    return {"linked": "eligibility>trend", "short": 7, "undo_redo_duplicate_remove": True}


def guard_and_risk(a):
    a.preset("规则趋势基础")
    original = a.compiled_digest()
    before = len(a.api("/strategy-pipeline-runs"))
    a.edit_number("trend", "短窗口", "9")
    a.button("执行当前方案").click()
    expect(a.frame.get_by_text(re.compile("图形修改尚未应用到策略草稿"))).to_be_visible(timeout=15_000)
    assert len(a.api("/strategy-pipeline-runs")) == before
    a.preset("规则趋势基础")
    original = a.compiled_digest()
    a.edit_number("@risk", "总仓位上限", "9")
    a.button("应用到策略草稿").click()
    expect(a.frame.locator(".graph-issues")).to_be_visible()
    current = a.compiled_digest()
    a.save("invalid-risk-comparison.json", {"before": original, "after": current, "definition": a.definition()})
    assert current == original, "Invalid graph must preserve the YAML that existed immediately before apply"
    a.save(
        "invalid-risk-evidence.json", {"issue": a.frame.locator(".graph-issues").inner_text(), "no_run_created": True}
    )
    a.preset("规则趋势基础")
    return {"unapplied_run_blocked": True, "invalid_risk_preserved_yaml": True}


def nested_ui(a):
    a.preset("多策略总组合")
    a.node("s:trend").dblclick()
    expect(a.frame.locator(".graph-breadcrumb")).to_contain_text("trend")
    a.edit_number("trend", "短窗口", "7")
    a.apply()
    definition = a.definition()
    assert definition["sleeves"][0]["definition"]["nodes"][1]["params"]["short"] == 7
    a.yaml_field().input_value()
    a.page.evaluate("history.back()")
    expect(a.frame.locator(".graph-breadcrumb button")).to_have_count(1)
    a.page.evaluate("history.forward()")
    expect(a.frame.locator(".graph-breadcrumb button")).to_have_count(2)
    a.button("全屏画布").click()
    a.node("trend").click()
    return {"child": "main/trend", "short": 7, "browser_back_forward": True}


def publish_backtest(a):
    a.preset("规则趋势基础")
    a.edit_number("trend", "短窗口", "7")
    a.apply()
    a.yaml_field()
    a.button("校验与预览").click()
    expect(a.textbox("生效预览（不训练、不调用模型）")).not_to_have_value("", timeout=30_000)
    a.button("保存发布版本").click()
    version = a.frame.get_by_role("spinbutton", name="发布版本ID", exact=True)
    expect(version).not_to_have_value("", timeout=30_000)
    row = a.run_ui()
    assert row["result"]["metrics"]["trade_count"] > 0
    a.save("ui-cli-consistency.json", a.cli_replay(row))
    a.button("全屏画布").click()
    a.node("trend").click()
    expect(a.frame.locator(".node-evidence pre")).to_contain_text("as_of")
    expect(a.frame.locator(".node-status").first).to_have_text("已完成", timeout=10_000)
    return {"run_id": row["id"], "version_id": row["version_id"], "metrics": row["result"]["metrics"]}


def layout_history(a):
    if a.button("退出全屏").is_visible():
        a.button("退出全屏").click()
    run_id = a.run_ids[-1]
    row = a.api("/strategy-pipeline-runs/" + run_id)
    plans = a.api("/strategy-pipelines")
    plan = next(
        p for p in plans if any(v["id"] == row["version_id"] for v in a.api(f"/strategy-pipelines/{p['id']}/versions"))
    )
    before = a.api(f"/strategy-pipelines/{plan['id']}/layout")
    a.button("全屏画布").click()
    box = a.node("trend").bounding_box()
    assert box
    a.page.mouse.move(box["x"] + 30, box["y"] + 20)
    a.page.mouse.down()
    a.page.mouse.move(box["x"] + 80, box["y"] + 60, steps=12)
    a.page.mouse.up()
    a.button("保存布局").click()
    expect(a.frame.locator(".graph-note")).to_have_text("布局已保存；计算定义未改变")
    after = a.api(f"/strategy-pipelines/{plan['id']}/layout")
    assert after["revision"] == before["revision"] + 1
    a.button("退出全屏").click()
    count = len(a.api("/strategy-pipeline-runs"))
    a.button("刷新历史").click()
    a.frame.get_by_role("listbox", name="历史运行", exact=True).click()
    a.frame.get_by_role("option").filter(has_text="backtest").first.click()
    a.button("打开历史").click()
    expect(a.textbox("实际运行状态")).to_have_value(re.compile("已完成"), timeout=30_000)
    assert len(a.api("/strategy-pipeline-runs")) == count
    a.save("layout-after.json", after)
    return {"layout_revision": after["revision"], "history_created_no_new_runs": True}


def theme_lifecycle(a):
    if a.button("退出全屏").is_visible():
        a.button("退出全屏").click()
    a.preset("形态模型级联")
    a.button("自动布局").click()
    a.node("tree").click()
    a.page.locator("#app-theme-toggle").click()
    expect(a.page.locator("html")).to_have_attribute("data-theme", "dark")
    a.button("全屏画布").click()
    a.page.screenshot(path=str(a.output / "dark-cascade.jpg"), type="jpeg", quality=90)
    a.button("退出全屏").click()
    a.page.locator("#app-theme-toggle").click()
    a.page.locator("#workspace-sidebar-toggle").click()
    expect(a.page.locator("#quant-workspace-shell")).to_have_class(re.compile("sidebar-collapsed"))
    a.page.locator("#workspace-sidebar-toggle").click()
    original = a.frame.locator(".graph-breadcrumb button").all_text_contents()
    a.page.locator('[data-workspace-module="market"]').click()
    a.page.frame_locator("iframe.workspace-frame.active").get_by_text("刷新行情", exact=True).first.wait_for(
        timeout=90_000
    )
    a.page.locator('[data-workspace-module="strategy"]').click()
    a.page.locator('[data-workspace-view-module="strategy"][data-workspace-view="workshop"]').click()
    expect(a.frame.locator(".graph-breadcrumb button")).to_have_text(original)
    assert len(a.page.context.pages) == 1
    return {"dark": True, "sidebar": True, "module_switch_preserved_graph": True, "one_tab": True}


def template_layout_isolation(a):
    a.preset("规则趋势基础")
    a.button("全屏画布").click()
    # Capturing a layout is a normal UI action, as are apply, export and navigating a subgraph.
    a.button("保存布局").click()
    expect(a.frame.locator(".graph-note")).to_have_text("布局已保存；计算定义未改变")
    a.preset("形态模型级联")
    a.button("全屏画布").click()
    positions = a.nodes().evaluate_all("""es => es.map(e => ({id:e.dataset.id,
        x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,
        width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))""")
    overlaps = []
    for index, first in enumerate(positions):
        for second in positions[index + 1 :]:
            width = min(first["x"] + first["width"], second["x"] + second["width"]) - max(first["x"], second["x"])
            height = min(first["y"] + first["height"], second["y"] + second["height"]) - max(first["y"], second["y"])
            if width > 2 and height > 2:
                overlaps.append([first["id"], second["id"]])
    a.save("template-layout-overlap.json", {"positions": positions, "overlaps": overlaps})
    assert not overlaps, f"Old template layout overlaps new nodes: {overlaps}"
    return {"overlaps": overlaps}


def sample_ui_backtest(a, name):
    a.preset(name)
    a.button("自动布局").click()
    row = a.run_ui()
    assert len(row["result"]["curve"]["dates"]) > 20
    return {
        "run_id": row["id"],
        "trades": row["result"]["metrics"]["trade_count"],
        "validation": row["result"].get("validation"),
        "source": row["result"]["source"],
    }


def cancel_ui(a):
    a.preset("行业轮动增强")
    a.button("自动布局").click()
    run_id = a.run_ui(mode="目标组合", end=a.config["current_date"], backend="Codex CLI", wait=False)
    expect(a.textbox("实际过程")).to_have_value(re.compile("Codex.*|model_fit"), timeout=90_000)
    a.button("取消当前运行").click()
    expect(a.textbox("实际运行状态")).to_have_value(re.compile("已取消"), timeout=60_000)
    row = a.api("/strategy-pipeline-runs/" + run_id)
    assert row["status"] == "cancelled"
    a.save("cancelled-run.json", row)
    a.save("cancelled-events.json", a.api("/strategy-pipeline-runs/" + run_id + "/events"))
    return {"run_id": run_id, "status": row["status"]}


def reload_same_preset(a):
    a.preset("规则趋势基础")
    a.node("trend").click()
    expect(a.frame.get_by_role("spinbutton", name="短窗口", exact=True)).to_have_value("5")
    a.edit_number("trend", "短窗口", "9")
    a.preset("规则趋势基础")
    a.node("trend").click()
    expect(a.frame.get_by_role("spinbutton", name="短窗口", exact=True)).to_have_value("5", timeout=5000)
    expect(a.button("撤销")).to_be_disabled()
    expect(a.frame.locator(".graph-note")).to_have_text("查看、拖动、缩放不会执行策略")
    return {"reloaded_original_short": 5}


def paper_same_day(a):
    a.start()
    a.preset("规则趋势基础")
    first = a.run_ui(mode="前向模拟", end=a.config["current_date"])
    account_id = first["result"]["account_id"]
    before = a.api(f"/strategy-pipeline-accounts/{account_id}")
    second = a.run_ui(mode="前向模拟", end=a.config["current_date"])
    after = a.api(f"/strategy-pipeline-accounts/{account_id}")
    assert second["result"]["account_id"] == account_id
    assert before["state"]["book"] == after["state"]["book"]
    a.save("paper-same-day.json", {"first": first, "second": second, "before": before, "after": after})
    return {"account_id": account_id, "same_day_ledger_unchanged": True}


def drag_and_invalid_import(a):
    a.start()
    a.button("全屏画布").click()
    a.frame.locator(".graph-palette").get_by_role("button", name="市场状态", exact=True).drag_to(
        a.frame.locator(".graph-canvas"),
        target_position={"x": 400, "y": 150},
    )
    expect(a.node("regime")).to_have_count(1)
    a.button("撤销").click()
    expect(a.node("regime")).to_have_count(0)
    with a.page.expect_download() as download:
        a.button("导出方案").click()
    exported = a.output / "invalid-import-base.json"
    download.value.save_as(exported)
    document = json.loads(exported.read_text(encoding="utf-8"))
    document["document"]["nodes"][0]["component"] = "unregistered_component"
    invalid = a.output / "rejected-import.json"
    invalid.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    before = a.frame.locator(".graph-breadcrumb button").all_text_contents()
    with a.page.expect_file_chooser() as pending:
        a.frame.locator(".graph-import").click()
    pending.value.set_files(invalid)
    expect(a.frame.locator(".graph-breadcrumb")).to_contain_text("仅支持本工坊导出的JSON方案")
    expect(a.frame.locator(".graph-breadcrumb button")).to_have_text(before)
    return {"palette_drag": True, "unknown_component_import_rejected": True}


def navigation_performance(a):
    a.start()
    fixture = PROJECT_ROOT / a.config["navigation_fixture"]
    with a.page.expect_file_chooser() as pending:
        a.frame.locator(".graph-import").click()
    pending.value.set_files(fixture)
    expect(a.frame.locator(".graph-breadcrumb")).to_contain_text("导航性能验收")
    a.node("s:group").dblclick()
    a.node("s:leaf").dblclick()
    expect(a.nodes()).to_have_count(44)
    field = a.frame.get_by_role("textbox", name="搜索阶段或组件", exact=True)
    field.fill("step20")
    field.press("Enter")
    expect(a.frame.locator(".property-heading strong")).to_have_text("step20")
    for _ in range(20):
        a.button("step21 ↗").click()
        a.button("step20 ↖").click()
    samples = json.loads(a.frame.locator(".strategy-graph-app").get_attribute("data-navigation-times"))
    ordered = sorted(samples)
    p95 = ordered[int(len(ordered) * 0.95) - 1]
    result = {
        "calculation_nodes": 40,
        "visible_nodes": 44,
        "samples_ms": samples,
        "p95_ms": p95,
        "measurement": "performance.now to Svelte tick; excludes test RPC and full paint",
    }
    a.save("navigation-performance.json", result)
    assert p95 <= 150, result
    return result


def fullscreen_fit(a):
    a.start()
    a.button("全屏画布").click()
    expect(a.button("退出全屏")).to_be_visible()
    expect(a.frame.locator(".graph-canvas")).to_have_attribute("data-fit-pending", "false")

    def geometry():
        boxes = a.nodes().evaluate_all(
            "es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,width:r.width}})"
        )
        canvas = a.frame.locator(".graph-canvas").bounding_box()
        width = max(b["x"] + b["width"] for b in boxes) - min(b["x"] for b in boxes)
        return {"node_span": width, "canvas_width": canvas["width"], "coverage": width / canvas["width"]}

    before = geometry()
    a.page.screenshot(path=str(a.output / "fullscreen-before-fit.jpg"), type="jpeg", quality=90)
    a.button("查看全图").click()
    after = geometry()
    result = {"before": before, "after_manual_fit": after}
    a.save("fullscreen-fit.json", result)
    assert before["coverage"] >= after["coverage"] * 0.85, "Entering fullscreen retained the smaller pre-resize fit"
    return result


def history_then_template(a):
    observations = []
    for _ in range(5):
        a.start()
        a.button("刷新历史").click()
        a.frame.get_by_role("listbox", name="历史运行", exact=True).click()
        a.frame.get_by_role("option").filter(has_text="backtest").first.click()
        a.button("打开历史").click()
        expect(a.textbox("实际运行状态")).to_have_value(re.compile("已完成"), timeout=30_000)
        a.dropdown("预置方案", "预置 / 形态模型级联")
        a.button("载入方案").click()
        a.yaml_field()
        # Wait for the visible YAML to change before comparing the independent graph value.
        expect(a.textbox("方案定义（YAML）")).to_have_value(re.compile("name: 形态模型级联"), timeout=15_000)
        try:
            expect(a.frame.locator(".graph-breadcrumb button").first).to_have_text("形态模型级联", timeout=5000)
            matched = True
        except AssertionError:
            matched = False
        observations.append(
            {
                "matched": matched,
                "graph": a.frame.locator(".graph-breadcrumb").inner_text(),
                "yaml_name": a.definition()["name"],
            }
        )
        a.save("history-template-observations.json", observations)
        if not matched:
            a.button("载入方案").scroll_into_view_if_needed()
            a.page.screenshot(path=str(a.output / "history-template-mismatch.jpg"), type="jpeg", quality=90)
    assert all(item["matched"] for item in observations), observations
    return observations


def saved_evidence_focus(a):
    """Reopen the frozen version and existing evidence without submitting another run."""
    a.start()
    root = PROJECT_ROOT / Path(a.config["output"]).parent
    previous = json.loads((root / "browser-final/browser.json").read_text(encoding="utf-8"))
    run_id = next(row["detail"]["run_id"] for row in previous["results"] if row["name"] == "06-publish-backtest")
    row = a.api("/strategy-pipeline-runs/" + run_id)
    plan_id = row["result"]["pipeline_id"]
    versions = a.api(f"/strategy-pipelines/{plan_id}/versions")
    version = next(item for item in versions if item["id"] == row["version_id"])
    label = f"已发布 / 规则趋势基础 · 方案#{plan_id} v{version['version']} · 版本#{version['id']}"
    a.dropdown("预置方案", label)
    prior = a.frame.locator(".strategy-graph-app").get_attribute("data-doc-id")
    a.button("载入方案").click()
    expect(a.frame.locator(".strategy-graph-app")).not_to_have_attribute("data-doc-id", prior)
    count = len(a.api("/strategy-pipeline-runs"))
    a.textbox("运行ID").fill(run_id)
    a.button("查看当前步骤").click()
    expect(a.frame.locator(".graph-footer")).to_contain_text(run_id)
    a.button("全屏画布").click()
    expect(a.frame.locator(".graph-canvas")).to_have_attribute("data-fit-pending", "false")
    a.node("trend").click()
    a.button("rules ↗").click()
    a.button("trend ↖").click()
    expect(a.frame.locator(".node-evidence pre")).to_contain_text("as_of")
    assert len(a.api("/strategy-pipeline-runs")) == count
    return {"run_id": run_id, "version_id": version["id"], "created_no_new_run": True}


def repeated_fullscreen_fit(a):
    observations = []
    for _ in range(5):
        observations.append(fullscreen_fit(a))
    a.save("repeated-fullscreen-fit.json", observations)
    return observations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    output = (PROJECT_ROOT / args.output).resolve()
    if not output.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Browser evidence must stay in this project")
    scenarios = {
        "01-seven-templates": templates_ui,
        "02-file-roundtrip": file_roundtrip,
        "03-edit-wire": edit_and_wire,
        "04-guards-risk": guard_and_risk,
        "05-nested-navigation": nested_ui,
        "06-publish-backtest": publish_backtest,
        "07-layout-history": layout_history,
        "08-theme-lifecycle": theme_lifecycle,
        "09-layout-isolation": template_layout_isolation,
        "10-model-ui-backtest": lambda a: sample_ui_backtest(a, "三模型共识"),
        "11-etf-ui-backtest": lambda a: sample_ui_backtest(a, "ETF多资产配置"),
        "12-multi-ui-backtest": lambda a: sample_ui_backtest(a, "多策略总组合"),
        "13-cancel-ui": cancel_ui,
        "14-reload-same-preset": reload_same_preset,
        "15-paper-same-day": paper_same_day,
        "16-drag-invalid-import": drag_and_invalid_import,
        "17-navigation-performance": navigation_performance,
        "18-fullscreen-fit": fullscreen_fit,
        "19-history-template-sync": history_then_template,
        "20-saved-evidence-focus": saved_evidence_focus,
        "21-repeated-fullscreen": repeated_fullscreen_fit,
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page.set_default_timeout(15_000)
        audit = GraphBrowser(page, config, output)
        try:
            audit.start()
            for name, action in scenarios.items():
                if not args.only or name in args.only:
                    audit.scenario(name, lambda action=action: action(audit))
        finally:
            audit.flush()
            browser.close()
    failures = [row["name"] for row in audit.results if not row["passed"]]
    logger.info("Graph browser acceptance failures={} output={}", failures, output)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
