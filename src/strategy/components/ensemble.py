"""Deterministic union, quorum, rank and voting without conflating missing with zero."""

from dataclasses import replace
from typing import Any

import numpy as np

from src.strategy.composition.config import config, fail
from src.strategy.composition.contracts import Observation


def combine(component: str, branches: list[dict[str, Observation]], params: dict[str, Any]) -> dict[str, Observation]:
    symbols = sorted(set().union(*(set(branch) for branch in branches)))
    valid = [
        {s: row for s, row in branch.items() if row.status == "pass" and row.value is not None} for branch in branches
    ]
    semantics = {(row.horizon, row.semantics) for branch in valid for row in branch.values()}
    if component != "merge" and len(semantics) > 1:
        raise fail("invalid", "incompatible horizons/semantics")
    references = {row.evidence.get("reference_universe") for branch in valid for row in branch.values()}
    if component != "merge" and len(references) > 1:
        raise fail("invalid", "incompatible reference universes")
    ranks = []
    for branch in valid:
        values = [float(row.value) for row in branch.values() if row.value is not None]
        ranks.append(
            {
                s: float(
                    (
                        sum(v < float(row.value or 0) for v in values)
                        + (sum(v == float(row.value or 0) for v in values) - 1) / 2
                    )
                    / (len(values) - 1)
                )
                if len(values) > 1
                else config()["defaults"]["rank_single"]
                for s, row in branch.items()
            }
        )
    weights = list(params.get("weights") or [1.0 for _ in branches])
    output = {}
    for symbol in symbols:
        observed = [(i, branch[symbol]) for i, branch in enumerate(valid) if symbol in branch]
        count = len(observed)
        required = len(branches) if params.get("method") == "intersection" else params["minimum"]
        denominator = sum(weights[i] for i, _ in observed)
        if count < required or denominator <= 0:
            output[symbol] = Observation(
                symbol, None, "unknown" if not count else "reject", "unknown", {"votes": count, "required": required}
            )
            continue
        base = observed[0][1]
        effective = {i: weights[i] for i, _ in observed}
        if component == "rank":
            families = {row.family for _, row in observed}
            for family in families:
                members = [i for i, row in observed if row.family == family]
                group = sum(weights[i] for i in members)
                factor = min(1.0, params["family_cap"] * denominator / group) if group else 0.0
                for i in members:
                    effective[i] *= factor
        if component == "merge":
            value = count / len(branches)
            passed = True
        elif component == "vote":
            value = (
                sum(
                    weights[i]
                    for i, row in observed
                    if row.evidence.get("component_kind") == "filter" or ranks[i][symbol] >= params["threshold"]
                )
                / denominator
            )
            passed = value >= params["threshold"]
        else:
            values = [ranks[i][symbol] for i, _ in observed]
            value = sum(effective[i] * ranks[i][symbol] for i, _ in observed) / denominator
            value = max(0.0, value - params.get("disagreement_penalty", 0.0) * float(np.std(values)))
            passed = True
        output[symbol] = replace(
            base,
            value=float(value),
            status="pass" if passed else "reject",
            family="ensemble",
            evidence={
                "branches": [
                    {"index": i, "raw": row.value, "rank": ranks[i][symbol], "weight": effective[i]}
                    for i, row in observed
                ],
                "coverage": count / len(branches),
            },
        )
    return output
