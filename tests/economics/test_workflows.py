"""REST, CLI, snapshot integrity and persisted report integration."""

import json

import pytest

from src.engine.economics.service import EconomicAnalysis
from src.engine.insights import execution
from src.engine.insights.config import insight_config
from src.engine.insights.service import InsightReportService
from src.frontend.services import FrontendService


def test_http_snapshot_period_peers_and_market_boundaries(economic_sources, client):
    macro = client.get("/api/v1/economics/macro?series=cpi,pmi").json()["data"]
    assert {row["series"] for row in macro["overview"]} == {"cpi", "pmi"}
    assert macro["historical_pit_eligible"] is False
    assert all(row["published_at"] is None for row in macro["observations"])
    data = client.get("/api/v1/economics/fundamentals/600519?peers=000001&period=2024-06-30").json()["data"]
    assert data["selected"]["report_period"] == "2024-06-30"
    assert not data["peers"] and any("mismatch" in gap for gap in data["gaps"])
    reopened = client.get("/api/v1/economics/snapshots/" + data["snapshot_id"]).json()["data"]
    assert reopened == data
    assert client.get("/api/v1/economics/macro?market=US").json()["code"] != 0
    assert client.get("/api/v1/economics/fundamentals/600519?period=bad").json()["code"] != 0


def test_cli_and_frontend_use_the_same_accounting_contract(economic_sources, cli_command):
    result = cli_command("economics", "fundamentals", "600519", "--period", "2025-03-31")["data"]
    assert result["selected"]["metrics"]["revenue_ttm"] == 800
    shown = FrontendService().economic_load("fundamentals", [], "600519", "2025-03-31", "", False)
    assert len(shown) == 5 and shown[3]["selected"]["metrics"]["revenue_ttm"] == 800
    assert cli_command("economics", "snapshot", result["snapshot_id"])["data"] == result


@pytest.mark.parametrize("kind", ["macro_analysis", "fundamental_analysis"])
def test_report_reuses_frozen_evidence_and_reopens(economic_sources, client, monkeypatch, kind):
    service = EconomicAnalysis()
    snapshot = service.macro(["cpi", "pmi"]) if kind == "macro_analysis" else service.fundamentals("600519")
    monkeypatch.setattr(execution, "validate_backend", lambda *args: {})

    def generate(prompt, payload, config, emit):
        return json.dumps(
            {
                "title": "Accounting integration",
                "summary": "Evidence-backed integration",
                "sections": [
                    {"heading": heading, "paragraphs": ["Read actual snapshot"], "source_ids": ["E1"]}
                    for heading in insight_config()["tasks"][kind]["sections"]
                ],
                "risks": [],
                "missing": [],
            }
        )

    monkeypatch.setattr(execution, "generate_text", generate)
    reports = InsightReportService()
    run = reports.start(
        {
            "kind": kind,
            "symbol": "600519" if kind == "fundamental_analysis" else "",
            "research_snapshot": snapshot["snapshot_id"],
        }
    )
    result = list(reports.follow(run["run_id"]))[-1]["run"]
    assert result["status"] == "partial", result
    evidence = json.loads((reports.store.directory(run["run_id"]) / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["sources"][0]["data"]["snapshot_id"] == snapshot["snapshot_id"]
    assert client.get(f"/api/v1/insights/runs/{run['run_id']}/files/report.html").status_code == 200
    assert FrontendService().economic_open(run["run_id"])[2].endswith("report.html")


def test_integrity_and_historical_claims_fail_closed(economic_sources):
    service = EconomicAnalysis()
    snapshot = service.macro(["cpi"])
    with pytest.raises(ValueError, match="PIT"):
        service.report_snapshot(snapshot["snapshot_id"], "macro_analysis", end_date="2020-01-01")
    with pytest.raises(ValueError):
        service.store.read("../.env")
    path = service.store.root / "snapshots" / (snapshot["snapshot_id"] + ".json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["historical_pit_eligible"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        service.store.read(snapshot["snapshot_id"])
