"""Browser audit of priority, analytical charts and rendered color scales."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright


def table_cells(frame: Any) -> list[dict[str, Any]]:
    return frame.locator("#home-details td[style*='--home-cell-color']").evaluate_all(
        """els => els.filter(el => el.getClientRects().length).map(el => ({
          text: el.innerText, accent: el.style.getPropertyValue('--home-cell-color'),
          intensity: el.style.getPropertyValue('--home-cell-strength'),
          background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color,
          surface: getComputedStyle(el).getPropertyValue('--surface').trim(),
        }))"""
    )


def channels(value: str) -> list[float]:
    if value.startswith("#"):
        return [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    values = [float(item) for item in re.findall(r"[\d.]+", value)[:3]]
    return values if value.startswith("color(srgb") else [item / 255 for item in values]


def assert_scales(cells: list[dict[str, Any]]) -> float:
    contrast_values = []
    for cell in cells:
        strength = float(cell["intensity"].strip().removesuffix("%")) / 100
        expected = [
            a * strength + b * (1 - strength)
            for a, b in zip(channels(cell["accent"].strip()), channels(cell["surface"]), strict=True)
        ]
        actual = channels(cell["background"])
        assert max(abs(a - b) for a, b in zip(expected, actual, strict=True)) < 0.01, cell
        luminances = []
        for rgb in (channels(cell["color"]), actual):
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in rgb]
            luminances.append(
                sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))
            )
        low, high = sorted(luminances)
        contrast_values.append((high + 0.05) / (low + 0.05))
    minimum = min(contrast_values)
    assert minimum >= 4.5, minimum
    return round(minimum, 2)


def run_audit(base_url: str, output: Path, width: int, height: int) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    ignored: list[str] = []
    with sync_playwright() as playwright:
        api_root = base_url.rstrip("/").replace("/app", "") + "/api/v1"
        account_response = requests.post(
            f"{api_root}/paper-accounts",
            json={"name": f"home-audit-{uuid4().hex[:8]}", "initial_capital": 1_000_000},
            timeout=20,
        )
        account_payload = account_response.json().get("data") or {}
        account_id = account_payload.get("account_id")
        if account_id:
            requests.post(
                f"{api_root}/paper-accounts/{account_id}/orders",
                json={"symbol": "300750", "side": "buy", "order_type": "market", "quantity": 100},
                timeout=20,
            )
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        def record_console(message: Any) -> None:
            if message.type == "error":
                (ignored if "ERR_NETWORK_ACCESS_DENIED" in message.text else errors).append(message.text)

        page.on("console", record_console)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: (
                errors.append(f"HTTP {response.status} {response.url}") if response.status >= 500 else None
            ),
        )
        page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
        frame = page.frame_locator("iframe.workspace-frame.active")
        expect(frame.locator("#home-refresh")).to_have_attribute("title", re.compile("重新读取"))
        expect(frame.locator("#home-trend")).to_have_attribute("title", re.compile("净值曲线"))
        expect(frame.locator("#home-risk-radar")).to_have_attribute("title", re.compile("仓位"))
        expect(frame.locator("#home-kpis .home-metric")).to_have_count(8, timeout=60_000)
        expect(frame.locator("#home-sectors .js-plotly-plot")).to_be_visible(timeout=60_000)
        expect(frame.locator("#home-trend .js-plotly-plot")).to_be_visible(timeout=60_000)
        page.wait_for_function(
            """() => {const doc=document.querySelector('iframe.workspace-frame.active')?.contentDocument;
            return ['home-trend','home-allocation','home-sectors','home-contribution'].every(id => {
                const plot = doc?.querySelector(`#${id} .js-plotly-plot`);
                return plot && ((plot.data?.length || 0) > 0 || plot.querySelector('.annotation-text'));
            });
            }""",
            timeout=60_000,
        )
        layout = frame.locator("#home-dashboard").evaluate(
            """root => ({width: innerWidth, documentWidth: document.documentElement.scrollWidth,
              trend: (()=>{let r=root.querySelector('#home-trend').getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height};})(),
              kpis: Array.from(root.querySelectorAll('#home-kpis .home-metric span')).map(el=>el.textContent),
              plots: Array.from(root.querySelectorAll('.js-plotly-plot')).map(el=>({types:(el.data||[]).map(t=>t.type),traces:el.data?.length||0})),
              tablesVisible: Array.from(root.querySelectorAll('.data-table')).filter(el=>el.getClientRects().length&&getComputedStyle(el).display!=='none').length,
            })"""
        )
        page.screenshot(path=str(output / f"home-{width}-light.png"))
        logger.info("Homepage initial layout | {}", layout)
        assert layout["documentWidth"] <= layout["width"] + 2, layout
        assert layout["tablesVisible"] == 0, layout
        assert {"scatter", "pie", "bar", "treemap", "scatterpolar"} <= {
            kind for plot in layout["plots"] for kind in plot["types"]
        }, layout
        if width >= 1280:
            assert layout["trend"]["bottom"] < height - 64, layout
        frame.locator("#home-sectors").scroll_into_view_if_needed()
        page.screenshot(path=str(output / f"home-{width}-analysis-light.png"))
        frame.get_by_role("button", name="完整数据与历史明细", exact=False).click()
        expect(frame.locator("#home-details td[style*='--home-cell-color']").first).to_be_attached(timeout=15_000)
        cells = table_cells(frame)
        logger.info("Rendered color scales | {}", cells[:12])
        assert cells, "No semantic styles reached the rendered table"
        assert any(cell["accent"].strip() == "#cf4058" for cell in cells), cells
        assert any(cell["accent"].strip() == "#138b78" for cell in cells), cells
        light_contrast = assert_scales(cells)
        frame.locator("#home-details td[style*='--home-cell-color']").first.hover()
        assert_scales(table_cells(frame))
        page.screenshot(path=str(output / f"home-{width}-tables-light.png"))
        assert frame.locator("body").evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        frame.get_by_role("button", name="完整数据与历史明细", exact=False).click()
        page.locator("#app-theme-toggle").click()
        expect(frame.locator("html")).to_have_attribute("data-theme", "dark")
        frame.locator("body").evaluate("() => scrollTo(0,0)")
        page.wait_for_timeout(300)
        page.screenshot(path=str(output / f"home-{width}-dark.png"))
        frame.locator("#home-sectors").scroll_into_view_if_needed()
        page.screenshot(path=str(output / f"home-{width}-analysis-dark.png"))
        frame.get_by_role("button", name="完整数据与历史明细", exact=False).click()
        dark_cells = table_cells(frame)
        dark_contrast = assert_scales(dark_cells)
        assert dark_cells and any(c["background"] != cells[0]["background"] for c in dark_cells), dark_cells
        page.screenshot(path=str(output / f"home-{width}-tables-dark.png"))
        frame.get_by_role("button", name="完整数据与历史明细", exact=False).click()
        frame.get_by_label("实盘账户", exact=True).check()
        expect(frame.locator("#home-data-status")).to_contain_text("broker", timeout=20_000)
        expect(frame.locator("#home-kpis")).to_contain_text("待 broker 回传")
        frame.get_by_label("模拟账户", exact=True).check()
        expect(frame.locator("#home-data-status")).to_contain_text("模拟账户")
        frame.get_by_role("button", name="刷新总览", exact=True).click()
        expect(frame.locator("#home-kpis .home-metric")).to_have_count(8)
        if width > 880:
            page.locator("#app-market-us").click()
            expect(frame.locator("#home-market-summary")).to_contain_text("S&P 500", timeout=30_000)
            expect(frame.locator("#home-kpis .home-metric")).to_have_count(8)
            page.locator("#app-market-cn").click()
            expect(frame.locator("#home-market-summary")).to_contain_text("上证指数", timeout=30_000)
            page.get_by_role("button", name="自定义仪表盘", exact=True).click()
            expect(frame.get_by_role("button", name="保存布局", exact=True)).to_be_visible()
            expect(frame.locator(".home-kpi-grid").last).to_be_visible(timeout=15_000)
            page.get_by_role("button", name="总览", exact=True).click()
            expect(frame.locator("#home-kpis")).to_be_visible()
            frame.locator("[data-home-module='ai']").first.click()
            expect(page.locator("iframe.workspace-frame.active")).to_have_attribute("data-module-key", "ai")
        browser.close()
    return {
        "layout": layout,
        "light_cells": cells,
        "dark_cells": dark_cells,
        "minimum_contrast": {"light": light_contrast, "dark": dark_contrast},
        "errors": errors,
        "external_errors": ignored,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8869/app/")
    parser.add_argument("--output", type=Path, default=Path("docs/audit/screenshots/2026-10-17-home"))
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    result = run_audit(args.base_url, args.output, args.width, args.height)
    report = args.output / f"home-{args.width}-report.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Homepage browser audit | errors={} report={}", len(result["errors"]), report)
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
