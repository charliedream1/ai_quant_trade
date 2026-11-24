"""Actual interpreter, public-source and browser acceptance; no model generation."""

import argparse
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep

import requests
from loguru import logger
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.core.config import get_settings  # noqa: E402
from src.core.process_control import stop_process_tree  # noqa: E402


def navigate(page, base, view):
    page.goto(base + "/app/?module=market&view=" + view, wait_until="domcontentloaded")
    return page.frame_locator("iframe.workspace-frame.active")


def inspect_pages(base, output, data_dir=None, log_offsets=None):
    data_dir = data_dir or output / "data"
    log_offsets = log_offsets or {}
    results = {}

    def checkpoint():
        (output / "page-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.add_init_script(
                "localStorage.setItem('all-in-one-ui-lang','en');localStorage.setItem('all-in-one-ui-market','cn')"
            )
            frame = navigate(page, base, "fundamentals")
            symbol = frame.locator("#fundamentals-symbol textarea")
            expect(symbol).to_have_value("600519", timeout=90000)
            frame.locator("#fundamentals-load").click()
            expect(frame.locator("#fundamentals-snapshot textarea")).not_to_have_value("", timeout=90000)
            results["financial_snapshot"] = frame.locator("#fundamentals-snapshot textarea").input_value()
            frame.locator("#financial-analysis-sections").get_by_role("radio", name="现金流量表").check()
            page.screenshot(path=str(output / "financials.png"))
            symbol.fill("")
            frame.locator("#fundamentals-load").click()
            expect(frame.get_by_text(re.compile("before loading financials")).first).to_be_visible(timeout=10000)
            results["blank_symbol_rejected"] = True
            checkpoint()
            frame = navigate(page, base, "quotes")
            expect(frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]')).to_be_visible(timeout=30000)
            frame.locator('#research-workspace-actions [data-research-refresh="market-quotes-refresh"]').click()
            plot = frame.locator("#market-sectors-plot .js-plotly-plot")
            expect(plot).to_be_visible(timeout=90000)
            values = plot.evaluate("element => Array.from(element.data[0].x)")
            results["rankings"] = {
                "positive": sum(value > 0 for value in values),
                "negative": sum(value < 0 for value in values),
                "rows": len(values),
            }
            page.screenshot(path=str(output / "rankings.png"))
            checkpoint()
            frame = navigate(page, base, "relations")
            expect(frame.locator("#rule-graph-start")).to_be_visible(timeout=30000)
            began = monotonic()
            frame.locator("#rule-graph-start").click()
            identifier = frame.locator("#rule-graph-run-id").locator("textarea,input").first
            expect(identifier).not_to_have_value("", timeout=10000)
            results["graph_ack_seconds"] = round(monotonic() - began, 3)
            assert results["graph_ack_seconds"] < 5
            key = identifier.input_value()
            folder = data_dir / "rule_graph_runs" / key
            deadline = monotonic() + 40
            while monotonic() < deadline:
                health = requests.get(base + "/api/v1/health", timeout=3)
                assert health.status_code == 200
                row = json.loads((folder / "run.json").read_text(encoding="utf-8"))
                if row["status"] not in {"queued", "running"}:
                    break
                sleep(0.25)
            assert row["status"] in {"completed", "partial"}, row
            results["rule_graph"] = row
            expect(frame.locator("#rule-graph-plot .js-plotly-plot")).to_be_visible(timeout=15000)
            frame.get_by_role("button", name=re.compile("Export.*JSON", re.I)).click()
            link = frame.locator("#rule-graph-download a[href*='graph.json']").filter(visible=True).first
            expect(link).to_be_visible(timeout=15000)
            with page.expect_download() as pending:
                link.click()
            downloaded = output / "saved-rule-graph.json"
            pending.value.save_as(str(downloaded))
            assert downloaded.read_bytes() == (folder / "graph.json").read_bytes()
            results["same_graph_export"] = True
            checkpoint()
            page.screenshot(path=str(output / "relations.png"))
            depth = frame.get_by_role("slider").filter(visible=True).first
            depth.focus()
            depth.press("End")
            frame.locator("#rule-graph-start").click()
            expect(identifier).not_to_have_value(key, timeout=10000)
            cancel_key = identifier.input_value()
            cancelled_at = monotonic()
            frame.locator("#rule-graph-cancel").click()
            cancel_folder = data_dir / "rule_graph_runs" / cancel_key
            deadline = monotonic() + 10
            while monotonic() < deadline:
                cancelled = json.loads((cancel_folder / "run.json").read_text(encoding="utf-8"))
                if cancelled["status"] not in {"queued", "running"}:
                    break
                sleep(0.1)
            assert cancelled["status"] == "cancelled", cancelled
            assert cancelled["request"]["depth"] == 5
            assert not (cancel_folder / "graph.json").exists()
            expect(frame.locator("#rule-graph-status")).to_contain_text("cancelled", timeout=10000)
            expect(frame.locator("#rule-graph-plot .js-plotly-plot")).to_have_count(0)
            expect(frame.locator("#rule-graph-download a[href*='graph.json']")).to_have_count(0)
            results["graph_cancellation"] = {
                "run_id": cancel_key,
                "status": cancelled["status"],
                "seconds": round(monotonic() - cancelled_at, 3),
                "old_result_cleared": True,
            }
            page.screenshot(path=str(output / "relations-cancelled.png"))
            checkpoint()
            page.goto(base + "/app/?module=admin&view=settings", wait_until="domcontentloaded")
            expect(frame.locator("#calendar-initialize")).to_be_visible(timeout=30000)
            frame.locator("#calendar-initialize").click()
            expect(frame.locator("#calendar-operation textarea")).not_to_have_value("", timeout=10000)
            results["calendar_initialize_button"] = True
            checkpoint()
            page.screenshot(path=str(output / "calendar.png"))
            page.set_viewport_size({"width": 420, "height": 900})
            navigate(page, base, "fundamentals")
            expect(frame.locator("#fundamentals-load")).to_be_visible(timeout=30000)
            page.screenshot(path=str(output / "financials-mobile.png"))
            page.set_viewport_size({"width": 1500, "height": 1050})
            page.goto(base + "/app/?module=dashboard&view=overview", wait_until="domcontentloaded")
            expect(frame.locator("#home-data-status")).not_to_contain_text("正在读取", timeout=60000)
            expect(frame.locator("#home-sectors .js-plotly-plot")).to_be_visible(timeout=60000)
            page.screenshot(path=str(output / "home.png"))
            logs = "\n".join(
                path.read_bytes()[log_offsets.get(str(path), 0) :].decode("utf-8", errors="replace")
                for path in (data_dir / "logs").glob("app_*.log")
            )
            counts = {
                key: sum("UI snapshot load |" in line and '"' + key + '"' in line for line in logs.splitlines())
                for key in ("home_account_snapshot", "home_market", "home_shared_news")
            }
            assert all(count == 1 for count in counts.values()), counts
            results["initial_home_source_loads"] = counts
            checkpoint()
        finally:
            browser.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interpreter", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--project-runtime",
        action="store_true",
        help="Use the existing project configuration/database, preserving generated results",
    )
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", args.port or 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.update(
        ALL_IN_ONE_RUNTIME_MODE="non-strict",
        ALL_IN_ONE_DATA_MODE="real",
        ALL_IN_ONE_DATA_DIR=str(output / "data"),
        ALL_IN_ONE_DB_PATH=str(output / "data/app.db"),
        ALL_IN_ONE_ACCESS_MODE="local",
        ALL_IN_ONE_HELP_DOCS_AUTO_BUILD="false",
        ALL_IN_ONE_CHANNELS_ENABLED="false",
        ALL_IN_ONE_LANGFUSE_ENABLED="false",
        ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED="false",
        PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1",
        ALL_IN_ONE_LOG_FILE_LEVEL="DEBUG",
        GRADIO_TEMP_DIR=str(output / "gradio-temp"),
    )
    if args.project_runtime:
        configured = get_settings()
        for key in (
            "ALL_IN_ONE_RUNTIME_MODE",
            "ALL_IN_ONE_DATA_MODE",
            "ALL_IN_ONE_DATA_DIR",
            "ALL_IN_ONE_DB_PATH",
            "ALL_IN_ONE_ACCESS_MODE",
            "ALL_IN_ONE_CHANNELS_ENABLED",
            "ALL_IN_ONE_LANGFUSE_ENABLED",
            "ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED",
        ):
            if key in os.environ:
                env[key] = os.environ[key]
            else:
                env.pop(key, None)
        data_dir = configured.data_dir.resolve()
        if configured.db_path.exists():
            with sqlite3.connect(configured.db_path.resolve().as_uri() + "?mode=ro", uri=True) as source:
                with sqlite3.connect(output / "database-before.db") as backup:
                    source.backup(backup)
    else:
        data_dir = output / "data"
    log_offsets = {str(path): path.stat().st_size for path in (data_dir / "logs").glob("app_*.log")}
    report = {}
    with (output / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [args.interpreter, "start.py", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
            start_new_session=sys.platform != "win32",
        )
        try:
            deadline = monotonic() + 90
            while monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Launcher exited before readiness")
                try:
                    response = requests.get(base + "/api/v1/health", timeout=2)
                    if response.ok:
                        report["health"] = response.json()
                        break
                except requests.RequestException:
                    pass
                sleep(0.25)
            assert report.get("health"), "Readiness deadline exceeded"
            assert report["health"]["data"]["trading_calendar"]["status"] == "ok"
            report.update(inspect_pages(base, output, data_dir, log_offsets))
            report["project_runtime"] = args.project_runtime
            report["status"] = "passed"
        except Exception as exc:
            report.update(status="failed", error=type(exc).__name__, message=str(exc))
        finally:
            if process.poll() is None:
                stop_process_tree(process)
                process.wait(timeout=10)
            with socket.socket() as probe:
                report["port_released"] = probe.connect_ex(("127.0.0.1", port)) != 0
            (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    console = (output / "server.log").read_text(encoding="utf-8")
    startup = console.split("Service ready", 1)[0]
    report["english_startup"] = not bool(re.search(r"[\u3400-\u9fff]", startup))
    report["normal_callback_console_lines"] = sum(
        "frontend action backend method started" in line or "frontend action backend method finished" in line
        for line in console.splitlines()
    )
    (output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Real browser acceptance status={} error={}", report["status"], report.get("message"))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
