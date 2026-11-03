"""Compile-time checks for factor parameters and typed graph connections."""

import math
from typing import Any

from .config import factor_config, factor_error, factor_set

FACTOR_COMPONENTS = {"factor_set", "factor_preprocess", "factor_select", "factor_score"}


def validate_parameters(component: str, params: dict[str, Any]) -> None:
    limits = factor_config()["limits"]
    if component == "factor_set":
        factor_set(params["set_name"])
    elif component == "factor_preprocess":
        if (
            params["method"] not in {"rank", "zscore"}
            or not 0 <= params["winsor_quantile"] < 0.5
            or params["min_assets"] < 2
        ):
            raise factor_error("invalid", component)
    elif component == "factor_select":
        if (
            not 0 <= params["min_coverage"] <= 1
            or not 0 <= params["min_rank_ic"] <= 1
            or not 0 < params["max_correlation"] <= 1
            or params["min_assets"] < 2
            or params["min_dates"] < 2
            or params["min_dates"] > params["lookback"]
            or params["lookback"] > limits["max_research_dates"]
            or params["groups"] < 2
            or params["horizon"] > limits["max_window"]
        ):
            raise factor_error("invalid", component)
    elif component == "factor_score":
        if (
            params["weighting"] not in {"equal", "icir"}
            or not 0 <= params["shrinkage"] <= 1
            or not 0 < params["max_factor_weight"] <= 1
            or not 0 <= params["min_coverage"] <= 1
            or params["minimum_factors"] > limits["max_factors"]
        ):
            raise factor_error("invalid", component)
    if any(isinstance(value, float) and not math.isfinite(value) for value in params.values()):
        raise factor_error("invalid", component)


def validate_connections(nodes: list[dict[str, Any]], output: str) -> None:
    lookup = {node["id"]: node for node in nodes}
    for node in nodes:
        component = node["component"]
        parents = [lookup.get(key, {}) for key in node["inputs"]]
        if component in FACTOR_COMPONENTS - {"factor_set"}:
            if len(parents) != 1 or parents[0].get("kind") != "factor":
                raise factor_error("invalid", node["id"] + ": factor panel required")
            if (
                component == "factor_score"
                and node["params"]["weighting"] == "icir"
                and parents[0].get("component") != "factor_select"
            ):
                raise factor_error("invalid", "ICIR requires factor_select")
        elif any(parent.get("kind") == "factor" for parent in parents):
            raise factor_error("invalid", node["id"] + ": score factors before using candidates")
        if component == "factor_preprocess" and parents[0].get("component") == "factor_select":
            raise factor_error("invalid", "preprocess must precede research selection")
    if lookup.get(output, {}).get("kind") == "factor":
        raise factor_error("invalid", "factor panels cannot be Portfolio inputs")
