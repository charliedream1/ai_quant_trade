"""Independent numerical fixtures and failure boundaries for actual research contracts."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from src.alpha_mining.config import policy
from src.alpha_mining.datasets import validate_dataset
from src.alpha_mining.factors import causal_checks, evaluate_expression, validate_expression
from src.alpha_mining.novelty import reference_overlap
from src.alpha_mining.pit import macro_snapshot, timestamp
from src.alpha_mining.research import label_panel
from src.alpha_mining.statistics import block_test, holm
from src.core.exceptions import BusinessError

FIXTURE = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("core.yaml").read_text(encoding="utf-8"))


def panel():
    return {
        "close": pd.DataFrame(FIXTURE["prices"], index=pd.bdate_range("2020-01-01", periods=8).strftime("%Y-%m-%d"))
    }


def test_registered_returns_matches_independent_hand_values():
    values = evaluate_expression({"op": "returns", "window": 2, "args": [{"field": "close"}]}, panel())
    expected = np.asarray([np.nan if value is None else value for value in FIXTURE["return_2d_AAA"]])
    np.testing.assert_allclose(values["AAA"], expected, equal_nan=True)


def test_nested_expression_has_no_future_or_security_order_leakage():
    expression = {"op": "rank", "args": [{"op": "mean", "window": 2, "args": [{"field": "close"}]}]}
    result = causal_checks(expression, panel())
    assert result["passed"] and result["future_perturbation"] and result["security_permutation"]


@pytest.mark.parametrize(
    "expression",
    [
        {"op": "lag", "window": -1, "args": [{"field": "close"}]},
        {"op": "eval", "args": [{"field": "close"}]},
        {"field": "future_return"},
        {"constant": 1},
        {"op": "mean", "window": True, "args": [{"field": "close"}]},
    ],
)
def test_unsafe_or_noncausal_definitions_are_rejected(expression):
    with pytest.raises(BusinessError):
        validate_expression(expression)


def test_holm_matches_reference_and_never_drops_failed_family_slots():
    assert holm(FIXTURE["holm_input"], 3) == pytest.approx(FIXTURE["holm_expected"])
    assert all(a >= b for a, b in zip(holm(FIXTURE["holm_input"], 5), FIXTURE["holm_expected"], strict=True))
    with pytest.raises(BusinessError):
        holm(FIXTURE["holm_input"], 2)


def test_block_inference_reproducibility_and_degenerate_evidence():
    p = FIXTURE["inference_policy"]
    values = list(np.linspace(-0.1, 0.2, 50))
    assert block_test(values, p) == block_test(values, p)
    assert block_test([1.0] * 50, p)["p_value"] == 1
    assert block_test([0.1], p)["status"] == "insufficient"


def test_macro_revision_is_not_visible_before_publication():
    rows = validate_dataset("macro", {"observations": FIXTURE["macro"]})["observations"]
    values, mapping = macro_snapshot(rows, "2020-03-01T12:00:00+00:00", 1)
    assert values == [{"id": "e1", "period": 0, "series": "growth", "value": 1.0}]
    assert mapping["e1"]["id"] == "original"
    assert "2020" not in str(values) and "original" not in str(values)
    changed, _ = macro_snapshot(rows, "2020-05-01T12:00:00+00:00", 1)
    assert changed[0]["value"] == -2


def test_unknown_timezone_is_rejected():
    with pytest.raises(BusinessError):
        timestamp("2020-03-01T12:00:00")


def test_reference_overlap_identifies_duplicate_and_inverse_without_missing_asset_bias():
    prices = panel()["close"]
    history = {
        symbol: [{"date": day, "close": value} for day, value in prices[symbol].items()]
        for symbol in reversed(prices.columns)
    }
    scores = prices.pct_change(2)
    days = list(prices.index[2:])
    result = reference_overlap(history, scores, days, FIXTURE["reference_factors"], len(prices.columns))
    assert result["registered_factors"]["momentum_2"] == {
        "mean_daily_rank_correlation": pytest.approx(1),
        "dates": len(days),
    }
    assert result["registered_factors"]["reversal_2"]["mean_daily_rank_correlation"] == pytest.approx(-1)
    scores.loc[days[-1], prices.columns[0]] = np.nan
    missing = reference_overlap(history, scores, days, FIXTURE["reference_factors"], len(prices.columns))
    assert missing["registered_factors"]["momentum_2"]["dates"] == len(days) - 1
    assert result["interpretation"] == "descriptive_overlap_not_proof_of_incremental_alpha"


def test_labels_use_next_open_and_do_not_cross_split_end():
    prices = panel()["close"]
    days = list(prices.index)
    labels = label_panel(prices, 2, days[:6])
    assert list(labels.index) == days[:3]
    assert labels.iloc[0]["AAA"] == pytest.approx(15 / 12 - 1)


def test_policy_cannot_hide_label_overlap_or_sample_shortage():
    with pytest.raises(BusinessError):
        policy({"horizon": 10, "embargo_sessions": 1})
    with pytest.raises(BusinessError):
        policy({"require_real_data": "false"})
