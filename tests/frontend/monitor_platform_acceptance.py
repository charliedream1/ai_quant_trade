"""Opt-in visible Gradio operations for monitoring, explanations and resource imports."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from time import perf_counter

from loguru import logger
from playwright.sync_api import expect, sync_playwright


def select(frame, label: str, option: str) -> None:
    frame.get_by_role("listbox", name=label, exact=True).click()
    frame.get_by_role("option", name=option, exact=True).click()


def monitor(page, base: str, output: Path) -> dict:
    started = perf_counter()
    page.goto(base + "/app/?module=market&view=factors", wait_until="domcontentloaded")
    frame = page.frame_locator("iframe.workspace-frame.active")
    expect(frame.get_by_role("button", name="运行因子监控", exact=True)).to_be_visible(timeout=90000)
    select(frame, "监控范围", "自定义股票池")
    frame.get_by_role("textbox", name="自定义股票代码（仅自定义范围使用）", exact=True).fill(
        "600519,300750,000001,688981,300124"
    )
    select(frame, "分析后端", "Qlib信号分析")
    frame.get_by_role("button", name="运行因子监控", exact=True).click()
    expect(frame.get_by_text("监控完成：", exact=False).first).to_be_visible(timeout=180000)
    expect(frame.locator(".chart-explanation:visible").first).to_be_visible()
    frame.locator(".chart-explanation:visible summary").first.click()
    expect(frame.locator(".chart-explanation:visible details[open]").first).to_contain_text("Spearman")
    frame.get_by_text("有效性、覆盖与原始截面", exact=True).click()
    expect(frame.get_by_text("Qlib信号分析：可用", exact=False).first).to_be_visible()
    assert "已到期" in frame.locator("body").inner_text()
    frame.get_by_role("button", name="运行因子监控", exact=True).scroll_into_view_if_needed()
    page.screenshot(path=str(output / "01-monitor-qlib.jpg"), type="jpeg", quality=85)
    return {"seconds": perf_counter() - started, "chart_help": frame.locator(".chart-explanation").count()}


def resources(page, base: str, output: Path, root: Path) -> dict:
    page.goto(base + "/app/?module=market&view=resources", wait_until="domcontentloaded")
    frame = page.frame_locator("iframe.workspace-frame.active")
    expect(frame.get_by_role("button", name="校验并预览", exact=True)).to_be_visible(timeout=90000)
    for label, filename in (("下载CSV模板", "template.csv"), ("下载Excel模板", "template.xlsx")):
        with page.expect_download() as download:
            frame.get_by_text(label, exact=True).click()
        download.value.save_as(str(output / filename))
    with page.expect_file_chooser() as chooser:
        frame.locator("#resource-pool-upload button").click()
    chooser.value.set_files(str(root / "egs/examples/resource_pool_templates/universe.csv"))
    expect(frame.locator("#resource-pool-upload")).to_contain_text(re.compile(r"universe\s*\.csv"))
    frame.get_by_role("button", name="校验并预览", exact=True).click()
    expect(frame.get_by_text("校验通过：", exact=False).first).to_be_visible(timeout=30000)
    page.screenshot(path=str(output / "02-resource-preview.jpg"), type="jpeg", quality=85)
    frame.get_by_role("button", name="确认导入", exact=True).click()
    expect(frame.get_by_text("导入完成：", exact=False).first).to_be_visible(timeout=30000)
    assert "000001" in frame.locator("body").inner_text()
    bad = output / "invalid.csv"
    bad.write_text("symbol,weight\n600519,NaN\n", encoding="utf-8")
    frame.locator("#resource-pool-upload").get_by_role("button", name="清除", exact=True).click()
    with page.expect_file_chooser() as chooser:
        frame.locator("#resource-pool-upload button").click()
    chooser.value.set_files(str(bad))
    expect(frame.locator("#resource-pool-upload")).to_contain_text(re.compile(r"invalid\s*\.csv"))
    frame.get_by_role("button", name="校验并预览", exact=True).click()
    expect(frame.get_by_text("校验未通过：", exact=False).first).to_be_visible(timeout=30000)
    page.screenshot(path=str(output / "03-resource-errors.jpg"), type="jpeg", quality=85)
    return {"template_downloads": 2, "leading_zero_visible": True, "bad_weight_rejected": True}


def relations(page, base: str, output: Path) -> dict:
    page.goto(base + "/app/?module=market&view=relations", wait_until="domcontentloaded")
    frame = page.frame_locator("iframe.workspace-frame.active")
    expect(frame.get_by_role("button", name="查询关系", exact=True)).to_be_visible(timeout=90000)
    frame.get_by_role("button", name="查询关系", exact=True).click()
    expect(frame.locator(".js-plotly-plot")).to_be_visible(timeout=60000)
    frame.get_by_role("button", name="适应全部 / 重新居中", exact=True).click()
    choice = frame.get_by_role("listbox", name="选择关系查看证据", exact=True)
    choice.click()
    frame.get_by_role("option").first.click()
    expect(frame.locator(".relation-evidence")).to_be_visible(timeout=15000)
    choice.press("Escape")
    graph = frame.locator(".js-plotly-plot")
    dimensions = graph.evaluate(
        "e=>({width:e.getBoundingClientRect().width,plotWidth:e._fullLayout.xaxis._length,left:e._fullLayout.xaxis._offset,x:e._fullLayout.xaxis.range,y:e._fullLayout.yaxis.range})"
    )
    assert dimensions["plotWidth"] / dimensions["width"] > 0.7, dimensions
    assert dimensions["left"] / dimensions["width"] < 0.15, dimensions
    frame.locator(".relation-evidence").screenshot(
        path=str(output / "04-relations-detail.jpg"), type="jpeg", quality=85
    )
    graph.scroll_into_view_if_needed()
    page.wait_for_timeout(350)
    page.screenshot(path=str(output / "04-relations-evidence.jpg"), type="jpeg", quality=85)
    page.locator("#workspace-sidebar-toggle").click()
    page.set_viewport_size({"width": 1680, "height": 1050})
    frame.get_by_role("button", name="适应全部 / 重新居中", exact=True).click()
    page.wait_for_timeout(350)
    graph.scroll_into_view_if_needed()
    page.screenshot(path=str(output / "05-relations-wide.jpg"), type="jpeg", quality=85)
    return dimensions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8890")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[2]
    results, errors, http_errors = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page.set_default_timeout(20000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: (
                http_errors.append({"url": response.url, "status": response.status})
                if response.status >= 400 and response.url.startswith(args.base_url)
                else None
            ),
        )
        try:
            for name, action in (
                ("monitor", lambda: monitor(page, args.base_url, args.output)),
                ("resources", lambda: resources(page, args.base_url, args.output, root)),
                ("relations", lambda: relations(page, args.base_url, args.output)),
            ):
                try:
                    result = {"name": name, "passed": True, "detail": action()}
                except Exception as exc:
                    result = {"name": name, "passed": False, "error": str(exc)}
                    page.screenshot(path=str(args.output / (name + "-failure.png")))
                    (args.output / (name + "-failure.txt")).write_text(
                        "\n".join(frame.locator("body").inner_text() for frame in page.frames), encoding="utf-8"
                    )
                results.append(result)
                logger.info("Browser scenario {}", result)
        finally:
            browser.close()
            (args.output / "browser.json").write_text(
                json.dumps(
                    {"results": results, "page_errors": errors, "http_errors": http_errors},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
    raise SystemExit(0 if all(row["passed"] for row in results) and not errors and not http_errors else 1)


if __name__ == "__main__":
    main()
