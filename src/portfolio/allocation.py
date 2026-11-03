"""Explicit numerical portfolio estimators with solver and feasibility diagnostics."""

from importlib import import_module
from typing import Any

import numpy as np
import pandas as pd

from src.strategy.composition.config import config, fail
from src.strategy.composition.contracts import Frame, Observation


def returns_panel(frame: Frame, symbols: list[str], window: int, minimum: int) -> pd.DataFrame:
    columns = {
        symbol: pd.Series({str(row["date"]): float(row["close"]) for row in frame.history[symbol]})
        for symbol in symbols
    }
    prices = pd.DataFrame(columns).sort_index().tail(window + 1)
    if (
        len(prices) < minimum + 1
        or prices.isna().any().any()
        or not np.isfinite(prices.to_numpy()).all()
        or (prices <= 0).any().any()
    ):
        raise fail("solver_failed", "aligned history")
    result = prices.pct_change(fill_method=None).iloc[1:]
    if not np.isfinite(result.to_numpy()).all():
        raise fail("solver_failed", "finite returns")
    return result


def covariance(returns: pd.DataFrame, shrinkage: float) -> np.ndarray:
    matrix = np.atleast_2d(np.cov(returns.to_numpy(), rowvar=False, ddof=1))
    return (1 - shrinkage) * matrix + shrinkage * np.diag(np.diag(matrix))


def _hrp(returns: pd.DataFrame, cov: np.ndarray, epsilon: float) -> np.ndarray:
    hierarchy = import_module("scipy.cluster.hierarchy")
    leaves_list, linkage = hierarchy.leaves_list, hierarchy.linkage
    squareform = import_module("scipy.spatial.distance").squareform

    correlation = returns.corr().fillna(0).to_numpy(copy=True)
    np.fill_diagonal(correlation, 1)
    distance = np.sqrt(np.maximum(0, (1 - np.clip(correlation, -1, 1)) / 2))
    order = list(leaves_list(linkage(squareform(distance, checks=False), method="single")))
    weights = np.ones(len(order))

    def cluster_variance(indices: list[int]) -> float:
        sub = cov[np.ix_(indices, indices)]
        inverse = 1 / np.maximum(np.diag(sub), epsilon)
        w = inverse / inverse.sum()
        return float(w @ sub @ w)

    clusters = [order]
    while clusters:
        next_clusters = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            midpoint = len(cluster) // 2
            left, right = cluster[:midpoint], cluster[midpoint:]
            lv, rv = cluster_variance(left), cluster_variance(right)
            fraction = rv / (lv + rv) if lv + rv > epsilon else 0.5
            weights[left] *= fraction
            weights[right] *= 1 - fraction
            next_clusters.extend([left, right])
        clusters = next_clusters
    return weights / weights.sum()


def allocate(
    method: str, observations: dict[str, Observation], frame: Frame, params: dict[str, Any]
) -> tuple[dict[str, float], dict[str, Any]]:
    selected = sorted(
        [r for r in observations.values() if r.status == "pass" and r.value is not None],
        key=lambda row: (-float(row.value or 0), row.symbol),
    )[: params["top_k"]]
    names = [row.symbol for row in selected]
    diagnostics: dict[str, Any] = {
        "method": method,
        "symbols": names,
        "status": "empty" if not names else "estimated",
        "cash": 1.0,
    }
    if not names:
        return {}, diagnostics
    if method in {"regime_fixed", "agent_budget"}:
        if any(row.semantics != "target_weight" for row in selected):
            raise fail("invalid", "regime_fixed requires frozen target weights")
        frozen = {row.symbol: float(row.value or 0) for row in selected}
        if sum(frozen.values()) > 1 + config()["defaults"]["epsilon"]:
            raise fail("invalid", "regime weights exceed capital")
        targets = {symbol: min(value * params["exposure"], params["max_weight"]) for symbol, value in frozen.items()}
        return targets, {**diagnostics, "cash": 1 - sum(targets.values()), "normalized": False}
    epsilon = config()["defaults"]["covariance_floor"]
    raw = np.ones(len(names))
    try:
        if method == "score":
            # Scores are allocation strengths only, never claims of positive absolute returns.
            raw = np.asarray([max(float(row.value or 0), 0) for row in selected])
            if raw.sum() <= epsilon:
                return {}, {**diagnostics, "status": "no_positive_strength"}
        elif method in {"inverse_volatility", "erc", "hrp", "minimum_variance"}:
            returns = returns_panel(frame, names, params["window"], params["min_observations"])
            cov = covariance(returns, params["shrinkage"])
            diagnostics.update(
                observations=len(returns), covariance=cov.tolist(), condition_number=float(np.linalg.cond(cov))
            )
            if (
                not np.isfinite(cov).all()
                or np.any(np.diag(cov) <= epsilon)
                or not np.isfinite(diagnostics["condition_number"])
            ):
                raise fail("solver_failed", "degenerate covariance")
            if method == "inverse_volatility":
                raw = 1 / np.sqrt(np.diag(cov))
            elif method == "hrp":
                raw = np.ones(1) if len(names) == 1 else _hrp(returns, cov, epsilon)
            else:
                minimize = import_module("scipy.optimize").minimize

                def objective(w):
                    variance = float(w @ cov @ w)
                    if method == "minimum_variance":
                        return variance / max(float(np.max(np.diag(cov))), epsilon)
                    contributions = w * (cov @ w) / max(variance, epsilon)
                    return float(np.sum((contributions - 1 / len(w)) ** 2))

                solution = minimize(
                    objective,
                    np.full(len(names), 1 / len(names)),
                    method="SLSQP",
                    bounds=[(0, 1)] * len(names),
                    constraints={"type": "eq", "fun": lambda w: float(w.sum() - 1)},
                    options={"maxiter": params["solver_iterations"], "ftol": params["solver_tolerance"]},
                )
                if (
                    not solution.success
                    or not np.isfinite(solution.x).all()
                    or abs(float(solution.x.sum()) - 1) > params["solver_tolerance"] ** 0.5
                ):
                    raise fail("solver_failed", str(solution.message))
                raw = np.maximum(solution.x, 0)
                diagnostics["solver"] = {
                    "success": True,
                    "iterations": int(solution.nit),
                    "objective": float(solution.fun),
                }
                diagnostics["risk_contributions"] = (raw * (cov @ raw) / max(float(raw @ cov @ raw), epsilon)).tolist()
        elif method != "equal":
            raise fail("invalid", method)
    except (ValueError, ImportError, np.linalg.LinAlgError) as exc:
        fallback = params["fallback"]
        if fallback == "none" or fallback == method:
            raise fail("solver_failed", str(exc)) from exc
        targets, alternative = allocate(fallback, observations, frame, {**params, "fallback": "none"})
        return targets, {**alternative, "requested_method": method, "fallback_reason": str(exc)}
    raw = raw / raw.sum() * params["exposure"]
    # Do not re-normalize after caps: the unallocated budget remains cash.
    targets = {name: min(float(weight), params["max_weight"]) for name, weight in zip(names, raw, strict=True)}
    diagnostics["cash"] = 1 - sum(targets.values())
    return targets, diagnostics


def strategy_budgets(
    sleeves: list[dict[str, Any]], histories: dict[str, list[float]], params: dict[str, Any], fallback: str
) -> tuple[dict[str, float], dict[str, Any]]:
    fixed = {s["id"]: float(s["budget"]) for s in sleeves}
    if not histories or any(len(histories.get(key, [])) < params["min_budget_observations"] + 1 for key in fixed):
        if fallback != "fixed_budget":
            raise fail("solver_failed", "strategy risk budget warmup")
        return fixed, {"method": "fixed_budget", "fallback_reason": "strategy risk budget warmup"}
    epsilon = config()["defaults"]["epsilon"]
    scales = {}
    for key in fixed:
        values = np.asarray(histories[key][-params["budget_window"] - 1 :])
        volatility = float(np.std(np.diff(values) / values[:-1]))
        if not np.isfinite(volatility) or volatility <= epsilon:
            if fallback == "fixed_budget":
                return fixed, {"method": "fixed_budget", "fallback_reason": "strategy zero volatility"}
            raise fail("solver_failed", "strategy zero volatility")
        scales[key] = 1 / volatility
    total = sum(fixed.values())
    return {key: total * value / sum(scales.values()) for key, value in scales.items()}, {
        "method": "strategy_inverse_volatility",
        "observations": {k: len(histories[k]) - 1 for k in fixed},
    }
