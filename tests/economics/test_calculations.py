"""Accounting periods and source semantics are checked independently of models."""

import copy

import pytest

from src.engine.economics.calculations import financial_periods, growth, numeric, statement_index


def test_quarter_conversion_ttm_and_yoy(observations):
    rows = financial_periods(observations, "600519", False)
    assert rows[1]["metrics"]["revenue_quarter"] == 150
    assert rows[-1]["metrics"]["revenue_ttm"] == 800
    assert rows[-1]["metrics"]["profit_ttm"] == 80
    assert rows[-1]["metrics"]["revenue_yoy"] == 100
    assert rows[-1]["metrics"]["roe"] == 3
    assert rows[-1]["metrics"]["known_debt_components"] == 23
    assert "not_total" in rows[-1]["statuses"]["known_debt_components"]


def test_incomplete_quarters_never_become_complete_ttm(observations):
    for source in observations.values():
        source["rows"] = [row for row in source["rows"] if row["REPORT_DATE"] != "2024-06-30"]
    rows = financial_periods(observations, "600519", False)
    assert rows[-1]["metrics"]["revenue_ttm"] is None
    assert rows[1]["metrics"]["revenue_quarter"] is None


@pytest.mark.parametrize(("base", "status"), [(0, "zero_base"), (-10, "loss_base"), (None, "missing")])
def test_zero_loss_and_missing_growth_bases(base, status):
    assert growth(20, base) == (None, status)


def test_industry_specific_metrics_are_not_fabricated(observations):
    row = financial_periods(observations, "600519", True)[-1]
    assert row["metrics"]["gross_margin"] is None
    assert row["metrics"]["roe"] is None
    assert row["metrics"]["known_debt_components"] is None


@pytest.mark.parametrize(
    ("key", "value"), [("SECURITY_CODE", "000001"), ("CURRENCY", "USD"), ("REPORT_DATE", "2024-02-29")]
)
def test_foreign_security_currency_and_nonquarter_dates_fail(observations, key, value):
    source = copy.deepcopy(observations["income"])
    source["rows"][0][key] = value
    with pytest.raises(ValueError):
        statement_index(source, "600519")


@pytest.mark.parametrize("value", [None, "-", True, "nan", "Infinity"])
def test_missing_and_nonfinite_values_remain_unknown(value):
    assert numeric(value) is None
