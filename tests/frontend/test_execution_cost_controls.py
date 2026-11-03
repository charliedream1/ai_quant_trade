"""Blank fee overrides inherit their profile; explicit zero retains its meaning."""

import pytest

from src.engine.execution.config import cost_config, resolve_costs
from src.frontend.features.execution_costs import build_cost_request


def test_blank_overrides_inherit_and_percent_zero_is_explicit():
    controls = cost_config()["ui"]["controls"]
    blanks = [""] * len(controls)
    assert build_cost_request("inherit", "research", None, "inherit", "{}", *blanks) is None
    selected = build_cost_request("cn_a", "research", None, "inherit", "{}", *blanks)
    assert resolve_costs(selected)["minimum_commission"] == 5
    values = [
        "0.04" if item["key"] == "buy_commission_rate" else "0" if item["key"] == "minimum_commission" else ""
        for item in controls
    ]
    override = build_cost_request("cn_a", "research", None, "inherit", "{}", *values)
    assert override["buy_commission_rate"] == 0.0004
    assert resolve_costs(override)["minimum_commission"] == 0


def test_advanced_override_requires_object():
    with pytest.raises(ValueError, match="JSON对象"):
        build_cost_request("inherit", "research", None, "inherit", "[]")
