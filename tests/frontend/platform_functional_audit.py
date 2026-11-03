"""Diagnose real browser actions against an explicitly isolated mock server."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import requests
import yaml
from loguru import logger
from playwright.sync_api import expect, sync_playwright


class Audit:
    def __init__(self, base_url: str, output: Path, fixture: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.config = yaml.safe_load(fixture.read_text(encoding="utf-8"))
        self.prefix = f"{self.config['name_prefix']}-{uuid4().hex[:8]}"
        self.session = requests.Session()
        self.session.trust_env = False
        self.results: list[dict[str, Any]] = []
        self.strategy_ids: list[int] = []

    def api(self, method: str, path: str, payload: dict | None = None) -> Any:
        response = self.session.request(method, f"{self.base_url}/api/v1{path}", json=payload, timeout=30)
        body = response.json()
        if body.get("code") != 0:
            raise RuntimeError(f"{response.status_code} {path}: {body}")
        return body["data"]

    def scenario(self, name: str, action: Callable[[], Any], page: Any = None) -> None:
        started = perf_counter()
        try:
            detail = action()
            self.results.append({"name": name, "status": "observed", "detail": detail})
        except Exception as exc:
            self.results.append({"name": name, "status": "failed", "error": str(exc)[:3000]})
            logger.warning("Diagnostic scenario failed | {} | {}", name, exc)
        self.results[-1]["duration_ms"] = round((perf_counter() - started) * 1000)
        if page is not None:
            page.screenshot(path=str(self.output / f"{name}.png"))

    def sample_backtests(self) -> list[dict[str, Any]]:
        results = []
        for index, example in enumerate(self.config["examples"]):
            strategy = self.api(
                "POST",
                "/strategies",
                {"name": f"{self.prefix}-{index}", "code": Path(example).read_text(encoding="utf-8")},
            )
            strategy_id = int(strategy["strategy_id"])
            self.strategy_ids.append(strategy_id)
            self.api("POST", f"/strategies/{strategy_id}/enable")
            payload = {key: self.config[key] for key in ("symbols", "start_date", "end_date")}
            payload.update(strategy_id=strategy_id, initial_capital=self.config["capital"])
            task = self.api("POST", "/backtests", payload)
            task_id = task["task_id"]
            metrics = self.api("GET", f"/backtests/{task_id}/performance")
            curve = self.api("GET", f"/backtests/{task_id}/equity-curve")
            trades = self.api("GET", f"/backtests/{task_id}/trades")
            attribution = self.api("GET", f"/backtests/{task_id}/attribution")
            assert len(curve["dates"]) == len(curve["equity"])
            results.append(
                {
                    "example": example,
                    "strategy_id": strategy_id,
                    "task_id": task_id,
                    "metrics": metrics,
                    "curve_dates": curve["dates"],
                    "trades": trades,
                    "attribution_summary": attribution["summary"],
                }
            )
        return results

    def paper_cycle(self) -> dict[str, Any]:
        account = self.api("POST", "/paper-accounts", {"name": self.prefix, "initial_capital": self.config["capital"]})
        account_id = account["account_id"]
        states = []
        for side in ("buy", "sell"):
            order = self.api(
                "POST",
                f"/paper-accounts/{account_id}/orders",
                {
                    "symbol": self.config["symbols"][1],
                    "side": side,
                    "order_type": "market",
                    "quantity": self.config["quantity"],
                },
            )
            overview = self.api("GET", f"/paper-accounts/{account_id}/overview")
            positions = self.api("GET", f"/paper-accounts/{account_id}/positions")
            states.append({"order": order, "overview": overview, "positions": positions})
        return {"account_id": account_id, "states": states}

    def qlib_backtest(self) -> dict[str, Any]:
        payload = {key: self.config[key] for key in ("symbols", "start_date", "end_date")}
        payload.update(strategy_id=self.strategy_ids[0], engine="qlib", initial_capital=self.config["capital"])
        response = self.session.post(f"{self.base_url}/api/v1/backtests", json=payload, timeout=30)
        return {"http_status": response.status_code, "body": response.json()}

    def open(self, page: Any, module: str, view: str) -> None:
        page.goto(f"{self.base_url}/app/{module}/?view={view}", wait_until="domcontentloaded")
        expect(page.locator(".gradio-container")).to_be_visible(timeout=90_000)
        view_label = {"management": "策略管理", "insights": "智能洞察", "main": "主界面", "backtest": "回测与模拟"}[
            view
        ]
        page.get_by_role("tab", name=view_label, exact=True).click()
        page.wait_for_timeout(500)

    def preset_import(self, page: Any) -> dict[str, Any]:
        self.open(page, "strategy", "management")
        page.get_by_role("tab", name="预制策略", exact=True).click()
        expect(page.locator(".preset-intro").first).not_to_be_empty()
        page.get_by_label("入库名称（可选，留空用策略标题）", exact=True).fill(f"{self.prefix}-ui")
        page.get_by_role("button", name="导入策略库", exact=True).click()
        expect(page.locator(".status-strip:visible").last).to_contain_text("已导入")
        return {"status": page.locator(".status-strip:visible").last.inner_text()}

    def browser_backtest(self, page: Any) -> dict[str, Any]:
        self.open(page, "simulation", "backtest")
        page.get_by_role("tab", name="回测", exact=True).click()
        page.get_by_label("策略 ID", exact=True).fill(str(self.strategy_ids[-1]))
        page.get_by_label("标的代码", exact=True).fill(",".join(self.config["symbols"]))
        page.get_by_label("开始日期", exact=True).fill(self.config["start_date"])
        page.get_by_label("结束日期", exact=True).fill(self.config["end_date"])
        page.get_by_role("button", name="开始回测", exact=True).click()
        expect(page.locator(".status-strip:visible").first).to_contain_text("已完成")
        task_id = int(float(page.get_by_label("任务 ID", exact=True).input_value()))
        page.get_by_role("button", name="查看结果", exact=True).click()
        expect(page.get_by_text("总收益率", exact=True).first).to_be_visible()
        return {"task_id": task_id, "status": page.locator(".status-strip:visible").first.inner_text()}

    def strategy_quick(self, page: Any) -> dict[str, Any]:
        self.open(page, "strategy", "management")
        page.get_by_role("tab", name="策略库", exact=True).click()
        page.get_by_label("策略 ID", exact=True).fill(str(self.strategy_ids[-1]))
        page.get_by_role("button", name="查看详情", exact=True).click()
        page.get_by_role("button", name="启用", exact=True).click()
        expect(page.locator(".status-strip:visible").first).to_contain_text("状态已更新")
        page.get_by_label("开始日期", exact=True).fill(self.config["start_date"])
        page.get_by_label("结束日期", exact=True).fill(self.config["end_date"])
        page.get_by_role("button", name="策略一键回测", exact=True).click()
        expect(page.locator(".status-strip:visible").last).to_contain_text("已完成")
        return {"status": page.locator(".status-strip:visible").last.inner_text()}

    def backtest_evidence(self, page: Any) -> dict[str, Any]:
        self.open(page, "simulation", "backtest")
        tasks = self.api("GET", "/backtests")
        task_id = tasks["items"][0]["task_id"]
        page.get_by_label("任务 ID", exact=True).fill(str(task_id))
        page.get_by_role("button", name="查看参数快照", exact=True).click()
        expect(page.get_by_text("回测参数快照", exact=True)).to_be_visible()
        page.get_by_role("button", name="导出交易日志", exact=True).click()
        expect(page.get_by_label("交易日志文件路径", exact=True)).not_to_have_value("")
        export_path = page.get_by_label("交易日志文件路径", exact=True).input_value()
        page.get_by_role("button", name="对比回测", exact=True).click()
        expect(page.get_by_text("已对比", exact=False)).to_be_visible()
        page.get_by_label("模拟账户名称（可选）", exact=True).fill(f"{self.prefix}-from-backtest")
        page.get_by_role("button", name="一键创建模拟账户", exact=True).click()
        expect(page.get_by_text("已创建", exact=False).last).to_be_visible()
        return {"task_id": task_id, "export_path": export_path}

    def browser_paper(self, page: Any) -> dict[str, Any]:
        self.open(page, "simulation", "backtest")
        page.get_by_role("tab", name="模拟交易", exact=True).click()
        page.get_by_label("账户名称", exact=True).fill(f"{self.prefix}-ui-paper")
        page.get_by_role("button", name="创建账户", exact=True).click()
        expect(page.locator(".status-strip:visible").first).to_contain_text("已创建")
        page.get_by_label("股票代码/名称", exact=True).fill(self.config["symbols"][1])
        page.get_by_role("button", name="提交委托", exact=True).click()
        expect(page.locator(".status-strip:visible").first).to_contain_text("订单 ID")
        return {"status": page.locator(".status-strip:visible").first.inner_text()}

    def enter_console(self, page: Any) -> dict[str, Any]:
        self.open(page, "ai", "main")
        task = page.get_by_label("输入任务", exact=True)
        task.fill(self.config["message"])
        task.press("Enter")
        page.wait_for_timeout(1800)
        after_enter = {
            "input": task.input_value(),
            "status": page.locator("#ai-console-status").inner_text(),
            "chat": page.locator("#ai-console-chat-history").inner_text(),
        }
        if task.input_value().strip():
            page.get_by_role("button", name="发送", exact=True).click()
            expect(page.locator("#ai-console-status")).to_contain_text("已回答")
        return {"after_enter": after_enter, "after_button": page.locator("#ai-console-status").inner_text()}

    def floating_cli(self, page: Any) -> dict[str, Any]:
        self.open(page, "strategy", "management")
        page.locator("#ai-floating-button").click()
        panel = page.locator("#ai-floating-panel")
        panel.get_by_role("tab", name="CLI 助手", exact=True).click()
        results = []
        for provider in ("codex", "trae"):
            panel.get_by_label("CLI", exact=True).click()
            panel.get_by_role("option", name=f"{provider} cli", exact=True).click()
            box = panel.get_by_label("消息", exact=True)
            box.fill(self.config["message"])
            box.press("Enter")
            page.wait_for_timeout(1000)
            results.append({"provider": provider, "after_enter": box.input_value()})
            panel.get_by_role("button", name="发送", exact=True).click()
            expected = "mock 模式未执行真实 Codex CLI" if provider == "codex" else "未接入真实对话"
            expect(panel.locator("#ai-cli-status")).to_contain_text(expected)
            results[-1]["chat"] = panel.locator("#ai-cli-history").inner_text()
        return {"providers": results, "status": panel.locator("#ai-cli-status").inner_text()}

    def floating_enter(self, page: Any) -> dict[str, Any]:
        self.open(page, "strategy", "management")
        page.locator("#ai-floating-button").click()
        panel = page.locator("#ai-floating-panel")
        panel.get_by_role("tab", name="模型问答", exact=True).click()
        task = panel.locator("textarea").first
        task.fill(self.config["message"])
        task.press("Enter")
        page.wait_for_timeout(1800)
        result = {"after_enter": task.input_value(), "status": panel.locator("#ai-chat-status").inner_text()}
        if task.input_value().strip():
            panel.get_by_role("button", name="发送", exact=True).click()
            expect(panel.locator("#ai-chat-status")).to_contain_text("mock-llm")
        result["after_button"] = panel.locator("#ai-chat-status").inner_text()
        return result

    def insights(self, page: Any) -> dict[str, Any]:
        started = perf_counter()
        self.open(page, "ai", "insights")
        before_refresh = {
            "summary_visible": page.locator(".dashboard-market-panel:visible").count(),
            "plots": page.locator(".js-plotly-plot:visible").count(),
        }
        page.get_by_role("button", name="刷新每日行情", exact=True).click()
        expect(page.locator(".dashboard-market-panel").first).to_be_visible(timeout=25_000)
        expect(page.locator(".js-plotly-plot:visible")).to_have_count(1, timeout=25_000)
        return {
            "before_refresh": before_refresh,
            "load_ms": round((perf_counter() - started) * 1000),
            "plots": page.locator(".js-plotly-plot:visible").count(),
        }

    def help_docs(self, page: Any) -> dict[str, Any]:
        page.goto(f"{self.base_url}/help-docs/troubleshooting/", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="CLI 只有日志、没有回复", exact=True)).to_be_visible()
        expect(page.get_by_text("Enter 不能发送", exact=True).first).to_be_visible()
        return {"title": page.title(), "updated_cli_boundary": True}

    def learning_docs(self, page: Any) -> dict[str, Any]:
        page.goto(f"{self.base_url}/app/knowledge/", wait_until="domcontentloaded")
        page.get_by_role("tab", name="学习专栏", exact=True).click()
        page.get_by_role("button", name="系统原理", exact=False).click()
        page.get_by_role("radio", name="测试与巡检原理说明", exact=True).check()
        expect(page.locator(".learning-reader").first).to_contain_text("功能正确性验收")
        page.get_by_role("button", name="刷新当前章节", exact=True).click()
        expect(page.locator(".learning-reader").first).to_contain_text("已刷新")
        return {"chapter": "测试与巡检原理说明", "updated": True}

    def run(self) -> None:
        self.scenario("api-small-backtests", self.sample_backtests)
        self.scenario("api-paper-roundtrip", self.paper_cycle)
        self.scenario("api-qlib-status", lambda: self.api("GET", "/qlib-workflows/status"))
        self.scenario("api-qlib-backtest", self.qlib_backtest)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.set_default_timeout(self.config["timeout_ms"])
            for name, action in (
                ("ui-preset-import", self.preset_import),
                ("ui-strategy-quick", self.strategy_quick),
                ("ui-backtest", self.browser_backtest),
                ("ui-backtest-evidence", self.backtest_evidence),
                ("ui-paper", self.browser_paper),
                ("ui-console-enter", self.enter_console),
                ("ui-floating-enter", self.floating_enter),
                ("ui-floating-cli", self.floating_cli),
                ("ui-insights", self.insights),
                ("ui-help-docs", self.help_docs),
                ("ui-learning-docs", self.learning_docs),
            ):
                self.scenario(name, partial(action, page), page)
            browser.close()
        report = self.output / "functional-report.json"
        report.write_text(json.dumps(self.results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        logger.info("Functional diagnosis completed | report={}", report)
        if any(item["status"] == "failed" for item in self.results):
            raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=Path("tests/fixtures/platform_functional_audit.yaml"))
    args = parser.parse_args()
    Audit(args.base_url, args.output, args.fixture).run()


if __name__ == "__main__":
    main()
