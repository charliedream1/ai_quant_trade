"""Real local HTTP, CLI and browser flows with explicitly simulated source/model data."""

import json
import re
from datetime import date
from pathlib import Path

import pytest
import yaml
from playwright.sync_api import expect, sync_playwright

from src.data.economics import EconomicDataSource
from src.engine.economics.service import EconomicAnalysis
from src.engine.insights import execution
from src.engine.insights.config import insight_config
from src.engine.insights.evidence import EvidenceCollector
from src.engine.insights.service import InsightReportService

SCENARIOS = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("simulation.yaml").read_text(encoding="utf-8"))


@pytest.fixture()
def simulated_runtime(economic_sources, monkeypatch):
    source = EconomicDataSource.fetch
    calls = []
    generations = []

    def fetch(self, name, **kwargs):
        calls.append((name, kwargs.get("symbol"), kwargs.get("refresh", False)))
        return {**source(self, name, **kwargs), "is_mock": True}

    def generate(prompt, payload, config, emit):
        identifier = payload["research_snapshot"]
        snapshot = EconomicAnalysis().store.read(identifier)
        assert snapshot["is_mock"] is True and identifier in prompt
        generations.append({"snapshot_id": identifier, "kind": payload["kind"]})
        report = SCENARIOS["report"]
        return json.dumps(
            {
                "title": report["title"],
                "summary": report["summary"],
                "sections": [
                    {"heading": heading, "paragraphs": [report["paragraph"]], "source_ids": ["E1"]}
                    for heading in config["tasks"][payload["kind"]]["sections"]
                ],
                "missing": report["missing"],
                "risks": [],
            }
        )

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    monkeypatch.setattr(execution, "validate_backend", lambda *args: {})
    monkeypatch.setattr(execution, "generate_text", generate)
    return calls, generations


def test_api_cli_selected_period_peer_and_frozen_report(simulated_runtime, client, cli_command):
    calls, generations = simulated_runtime
    snapshot = cli_command(
        "economics",
        "fundamentals",
        "600519",
        "--period",
        SCENARIOS["selected_period"],
        "--peers",
        SCENARIOS["matched_peer"] + "," + SCENARIOS["matched_peer_alias"],
    )["data"]
    assert snapshot["selected"]["metrics"]["revenue_quarter"] == 150
    assert len(snapshot["peers"]) == 1 and len(calls) == 8
    assert len(snapshot["periods"]) == 2 and snapshot["is_mock"] is True
    before = len(calls)
    result = cli_command(
        "insight",
        "run",
        "--kind",
        "fundamental_analysis",
        "--symbol",
        "600519",
        "--research-snapshot",
        snapshot["snapshot_id"],
        stream=True,
    )
    run = next(item["data"] for item in reversed(result) if item.get("type") == "result")
    if "data" in run:
        run = run["data"]
    report = InsightReportService().detail(run["run_id"])
    assert report["status"] == "partial" and len(calls) == before
    assert len(generations) == 1
    evidence = client.get(f"/api/v1/insights/runs/{run['run_id']}/files/evidence.json").json()
    assert evidence["is_mock"] is True
    assert [row["report_period"] for row in evidence["sources"][0]["data"]["periods"]] == [
        "2024-03-31",
        SCENARIOS["selected_period"],
    ]
    html = client.get(f"/api/v1/insights/runs/{run['run_id']}/files/report.html").text
    assert SCENARIOS["report"]["summary"] in html


def test_browser_simulated_reports_preview_and_reopen(simulated_runtime, cli_command, tmp_path):
    calls, generations = simulated_runtime
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1100})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=market&view=macro", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#macro-load")).to_be_visible(timeout=90000)
            assert not calls and not generations
            for kind in ("macro", "fundamentals"):
                if kind == "fundamentals":
                    page.locator('[data-workspace-view="fundamentals"][data-workspace-view-module="market"]').click()
                    frame.locator("#fundamentals-symbol textarea").fill("600519")
                    frame.get_by_label("报告期（YYYY-MM-DD，留空为最新）", exact=True).fill(
                        SCENARIOS["selected_period"]
                    )
                frame.locator("#" + kind + "-load").click()
                expect(frame.locator("#" + kind + "-status")).to_contain_text("模拟来源", timeout=30000)
                source_count = len(calls)
                frame.locator("#" + kind + "-report").click()
                expect(frame.locator("#" + kind + "-report-status textarea")).to_have_value(
                    re.compile(r"partial"), timeout=30000
                )
                preview = frame.frame_locator("#" + kind + "-report-preview iframe")
                expect(preview.get_by_text(SCENARIOS["report"]["summary"], exact=True)).to_be_visible()
                assert len(calls) == source_count
                frame.get_by_role("button", name="重新打开报告", exact=True).click()
                expect(preview.get_by_text(SCENARIOS["report"]["summary"], exact=True)).to_be_visible()
                assert len(calls) == source_count
                frame.locator("#" + kind + "-report-preview").scroll_into_view_if_needed()
                page.screenshot(path=str(tmp_path / (kind + "-simulation.png")))
            assert len(generations) == 2
        finally:
            browser.close()


def test_legacy_stock_attachment_reuses_explicit_company_snapshot(simulated_runtime):
    calls, _ = simulated_runtime
    service = EconomicAnalysis()
    snapshot = service.fundamentals("600519", period=SCENARIOS["selected_period"])
    before = len(calls)
    payload = {
        "kind": "single_stock_analysis",
        "symbol": "600519",
        "market": "CN",
        "end_date": date.today().isoformat(),
        "research_snapshot": snapshot["snapshot_id"],
        "include_fundamentals": True,
    }
    collector = EvidenceCollector(payload, insight_config(), lambda *args: None)
    collector._attach_fundamentals()
    assert len(calls) == before
    assert collector.sources[0]["data"]["selected"]["report_period"] == SCENARIOS["selected_period"]
    assert collector.sources[0]["is_mock"] is True
    payload["symbol"] = SCENARIOS["matched_peer"]
    wrong = EvidenceCollector(payload, insight_config(), lambda *args: None)
    wrong._attach_fundamentals()
    assert not wrong.sources and wrong.gaps
