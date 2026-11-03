"""Opt-in real-source browser acceptance using the explicitly selected free Hy3 model."""

import json
import os
import re
from pathlib import Path

import pytest
import yaml
from playwright.sync_api import expect, sync_playwright

import src.core.config as config_module
from src.engine.economics.store import EconomicStore
from src.engine.insights.service import InsightReportService
from tests.knowledge.workbuddy_hy3_runtime import Hy3Runtime, openai_bridge

pytestmark = pytest.mark.skipif(
    os.environ.get("ECONOMIC_HY3_LIVE") != "1", reason="Explicit real-source and free-model acceptance only"
)


def test_real_economic_browser_and_reports(client, cli_command, monkeypatch):
    policy = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("live.yaml").read_text(encoding="utf-8"))
    runtime_policy = yaml.safe_load(Path(policy["adapter_policy"]).read_text(encoding="utf-8"))
    runtime_policy["runtime"].update(
        timeout_seconds=policy["runtime_timeout_seconds"], system_prompt=policy["system_prompt"]
    )
    output = Path(os.environ[policy["output_env"]])
    output.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "real")
    config_module._SETTINGS = None
    runtime = Hy3Runtime(runtime_policy, output)
    results = []
    with openai_bridge(runtime) as endpoint:
        model = client.post(
            "/api/v1/llm-models",
            json={
                "name": "Economic Hy3 acceptance",
                "model_name": "hy3",
                "base_url": endpoint,
                "api_backend": "openai",
                "rpm": 5,
                "timeout_seconds": policy["model_timeout_seconds"],
                "max_tokens": policy["output_tokens"],
            },
        ).json()["data"]
        assert model["api_backend"] == "openai"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1500, "height": 1100})
                page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
                page.goto(cli_command.base_url + "/app/?module=market&view=macro", wait_until="domcontentloaded")
                frame = page.frame_locator("iframe.workspace-frame.active")
                for kind in ("macro", "fundamentals"):
                    if kind == "fundamentals":
                        page.locator(
                            '[data-workspace-view="fundamentals"][data-workspace-view-module="market"]'
                        ).click()
                        frame.locator("#fundamentals-symbol textarea").fill(policy["symbol"])
                    frame.locator("#" + kind + "-load").click(timeout=90000)
                    expect(frame.locator("#" + kind + "-status")).to_contain_text("当前公开版本", timeout=60000)
                    before = len(runtime.records)
                    frame.locator("#" + kind + "-report").click()
                    expect(frame.locator("#" + kind + "-report-status textarea")).to_have_value(
                        re.compile(r"partial|completed|failed"), timeout=policy["browser_timeout_ms"]
                    )
                    run_id = frame.locator("#" + kind + "-run-id textarea").input_value()
                    service = InsightReportService()
                    run = service.detail(run_id)
                    assert run["status"] == "partial", run
                    assert len(runtime.records) > before
                    directory = service.store.directory(run_id)
                    evidence = json.loads((directory / "evidence.json").read_text(encoding="utf-8"))
                    snapshot = EconomicStore().read(evidence["sources"][0]["data"]["snapshot_id"])
                    assert snapshot["is_mock"] is False and snapshot["historical_pit_eligible"] is False
                    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
                    assert all(section["source_ids"] == ["E1"] for section in report["sections"])
                    for name in ("report.html", "report.json", "evidence.json", "events.jsonl", "request.json"):
                        (output / (kind + "-" + name)).write_bytes((directory / name).read_bytes())
                    frame.locator("#" + kind + "-report-preview").scroll_into_view_if_needed()
                    page.screenshot(path=str(output / (kind + "-browser.png")))
                    results.append(
                        {
                            "kind": kind,
                            "run_id": run_id,
                            "duration_ms": run["duration_ms"],
                            "snapshot_id": snapshot["snapshot_id"],
                            "model_calls": len(runtime.records) - before,
                        }
                    )
            finally:
                browser.close()
    assert runtime.records and all(
        set(row["model_usage"]) == {"hy3"} and row["native_tool_calls"] == 0 for row in runtime.records
    )
    (output / "acceptance.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
