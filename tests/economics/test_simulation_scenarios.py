"""Independent accounting oracles and adversarial research-scope simulations."""

from datetime import date
from pathlib import Path

import pytest
import yaml

from src.data.economics import EconomicDataSource
from src.engine.economics.calculations import financial_periods
from src.engine.economics.config import economics_config
from src.engine.economics.service import EconomicAnalysis
from src.engine.insights.config import insight_config
from src.engine.insights.evidence import EvidenceCollector

SCENARIOS = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("simulation.yaml").read_text(encoding="utf-8"))


def test_all_financial_periods_match_hand_calculated_oracle(observations):
    rows = financial_periods(observations, "600519", False)
    for actual, expected in zip(rows, SCENARIOS["financial_expectations"], strict=True):
        assert actual["report_period"] == expected["period"]
        for key in ("revenue_quarter", "profit_quarter", "revenue_ttm", "profit_ttm"):
            assert actual["metrics"][key] == expected[key]
        assert actual["metrics"]["operating_cashflow_quarter"] == expected["cashflow_quarter"]
    assert rows[-1]["metrics"]["debt_asset_ratio"] == pytest.approx(500 / 1400 * 100)
    assert rows[-1]["metrics"]["cash_profit_ratio"] == 1


def test_consolidated_profit_uses_same_scope_tax_derivation(observations):
    for row in observations["income"]["rows"]:
        row["NETPROFIT"] = None
        row["TOTAL_PROFIT"], row["INCOME_TAX"] = 40, 10
    row = financial_periods(observations, "600519", False)[-1]
    assert row["metrics"]["consolidated_profit"] == 30
    assert row["metrics"]["cash_profit_ratio"] == pytest.approx(22 / 30)
    observations["income"]["rows"][-1]["INCOME_TAX"] = None
    missing = financial_periods(observations, "600519", False)[-1]
    assert missing["metrics"]["cash_profit_ratio"] is None


@pytest.mark.parametrize("name", list(economics_config()["macro"]))
def test_macro_units_zero_negative_future_missing_and_order(economic_sources, monkeypatch, name):
    original = EconomicDataSource.fetch
    definition = economics_config()["macro"][name]

    def fetch(self, series, **kwargs):
        source = original(self, series, **kwargs)
        source["rows"] = [
            {
                definition["date"]: row["period"].replace("-", "")[:6]
                if name == "social_finance" and row["period"] != "invalid"
                else row["period"],
                definition["field"]: row["value"],
            }
            for row in reversed(SCENARIOS["macro_rows"])
        ]
        return source

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    result = EconomicAnalysis().macro([name])
    assert [row["value"] for row in result["observations"]] == [0, -2.5, 4.2]
    assert result["overview"][0]["stale"] is True
    assert result["overview"][0]["unit"] == definition["unit"]
    assert result["overview"][0]["basis"] == definition["basis"]
    assert result["overview"][0]["frequency"] == definition["frequency"]


def test_source_failure_preserves_only_available_series(economic_sources, monkeypatch):
    original = EconomicDataSource.fetch

    def fetch(self, name, **kwargs):
        if name == SCENARIOS["source_failure"]:
            raise TimeoutError("Simulated source timeout")
        return original(self, name, **kwargs)

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    result = EconomicAnalysis().macro(["cpi", "pmi"])
    assert [row["series"] for row in result["overview"]] == ["pmi"]
    assert "cpi: TimeoutError" in result["gaps"]
    with pytest.raises(ValueError):
        EconomicAnalysis().macro(["cpi"])


def test_selected_report_period_limits_trends_and_report_evidence(economic_sources):
    service = EconomicAnalysis()
    snapshot = service.fundamentals("600519", period=SCENARIOS["selected_period"])
    assert all(row["report_period"] <= snapshot["selected"]["report_period"] for row in snapshot["periods"])
    payload = {
        "kind": "fundamental_analysis",
        "symbol": "600519",
        "market": "CN",
        "end_date": date.today().isoformat(),
        "research_snapshot": snapshot["snapshot_id"],
    }
    evidence = EvidenceCollector(payload, insight_config(), lambda *args: None).collect()
    periods = evidence["sources"][0]["data"]["periods"]
    assert all(row["report_period"] <= SCENARIOS["selected_period"] for row in periods)


def test_aliases_do_not_duplicate_matching_peer_samples(economic_sources):
    result = EconomicAnalysis().fundamentals(
        "600519", peers=[SCENARIOS["matched_peer"], SCENARIOS["matched_peer_alias"], SCENARIOS["mismatched_peer"]]
    )
    assert [row["symbol"] for row in result["peers"]] == [SCENARIOS["matched_peer"]]
    assert all(row["report_period"] == result["selected"]["report_period"] for row in result["peers"])
    assert any("mismatch" in gap for gap in result["gaps"])


def test_simulated_source_marker_survives_snapshot_and_report(economic_sources, monkeypatch):
    original = EconomicDataSource.fetch

    def fetch(self, name, **kwargs):
        return {**original(self, name, **kwargs), "is_mock": True}

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    snapshot = EconomicAnalysis().macro(["cpi"])
    assert snapshot["is_mock"] is True
    payload = {
        "kind": "macro_analysis",
        "market": "CN",
        "end_date": date.today().isoformat(),
        "research_snapshot": snapshot["snapshot_id"],
    }
    evidence = EvidenceCollector(payload, insight_config(), lambda *args: None).collect()
    assert evidence["is_mock"] is True and evidence["sources"][0]["is_mock"] is True


def test_historical_stock_report_never_attaches_current_financial_revision(economic_sources):
    payload = {
        "kind": "single_stock_analysis",
        "symbol": "600519",
        "market": "CN",
        "end_date": "2020-01-01",
        "include_fundamentals": True,
    }
    collector = EvidenceCollector(payload, insight_config(), lambda *args: None)
    collector._attach_fundamentals()
    assert not collector.sources
    assert collector.gaps


def test_missing_cashflow_statement_does_not_become_zero(economic_sources, monkeypatch):
    original = EconomicDataSource.fetch

    def fetch(self, name, **kwargs):
        if name == "cashflow":
            raise TimeoutError("Simulated cash-flow outage")
        return original(self, name, **kwargs)

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    snapshot = EconomicAnalysis().fundamentals("600519")
    assert snapshot["selected"]["metrics"]["operating_cashflow"] is None
    assert snapshot["selected"]["metrics"]["operating_cashflow_ttm"] is None
    assert "cashflow" in snapshot["selected"]["missing_statements"]
    assert any("cashflow" in gap for gap in snapshot["gaps"])


def test_mock_analysis_has_no_external_network_dependency(economic_sources, monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail("Simulated analysis must not make external requests")

    monkeypatch.setattr(EconomicDataSource, "_request", refused)
    assert EconomicAnalysis().macro(["cpi"])["overview"]
    assert EconomicAnalysis().fundamentals("600519")["selected"]


def test_simulated_peer_marks_mixed_comparison_as_simulated(economic_sources, monkeypatch):
    original = EconomicDataSource.fetch

    def fetch(self, name, **kwargs):
        result = original(self, name, **kwargs)
        return {**result, "is_mock": str(kwargs.get("symbol", "")).startswith(SCENARIOS["matched_peer"])}

    monkeypatch.setattr(EconomicDataSource, "fetch", fetch)
    snapshot = EconomicAnalysis().fundamentals("600519", peers=[SCENARIOS["matched_peer"]])
    assert snapshot["is_mock"] is True
    assert snapshot["peers"][0]["is_mock"] is True
    assert economics_config()["messages"]["simulated"] in snapshot["gaps"]


def test_older_frozen_snapshot_is_filtered_when_reported(economic_sources, observations):
    service = EconomicAnalysis()
    snapshot = service.fundamentals("600519", period=SCENARIOS["selected_period"])
    older_shape = service.store.save({**snapshot, "periods": financial_periods(observations, "600519", False)})
    payload = {
        "kind": "fundamental_analysis",
        "symbol": "600519",
        "market": "CN",
        "end_date": date.today().isoformat(),
        "research_snapshot": older_shape["snapshot_id"],
    }
    evidence = EvidenceCollector(payload, insight_config(), lambda *args: None).collect()
    assert len(evidence["sources"][0]["data"]["periods"]) == 2
