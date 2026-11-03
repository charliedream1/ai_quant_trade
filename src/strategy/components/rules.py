"""Point-in-time price/volume rules with observable numeric explanations."""

from typing import Any

import numpy as np
import pandas as pd

from src.strategy.composition.config import config
from src.strategy.composition.contracts import Frame, Observation


def atr(rows: list | tuple, window: int) -> float:
    if len(rows) < window + 1:
        return 0.0
    return float(
        np.mean(
            [
                max(
                    float(row["high"]) - float(row["low"]),
                    abs(float(row["high"]) - float(prior["close"])),
                    abs(float(row["low"]) - float(prior["close"])),
                )
                for prior, row in zip(rows[-window - 1 : -1], rows[-window:], strict=True)
            ]
        )
    )


def _rule(component: str, rows: tuple, p: dict[str, Any]) -> tuple[float, bool, dict[str, Any]]:
    c = np.asarray([float(r["close"]) for r in rows])
    v = np.asarray([float(r.get("volume") or 0) for r in rows])
    needed = max([int(p[key]) for key in ("window", "long", "slow") if key in p] or [1]) + 1
    if len(c) < needed or not np.isfinite(c).all() or (c <= 0).any():
        raise ValueError("history")
    w = int(p.get("window", needed - 1))
    details: dict[str, Any] = {"close": float(c[-1]), "observations": len(c)}
    if component in {"momentum", "momentum_volume"}:
        value = float(c[-1] / c[-w - 1] - 1)
        ratio = float(v[-1] / v[-w - 1 : -1].mean()) if v[-w - 1 : -1].mean() > 0 else 0.0
        details.update(momentum=value, volume_ratio=ratio)
        return value, component == "momentum" or (value > p["min_return"] and ratio >= p["min_volume_ratio"]), details
    if component in {"trend", "pullback"}:
        fast, slow = float(c[-p["short"] :].mean()), float(c[-p["long"] :].mean())
        value = fast / slow - 1
        details.update(fast=fast, slow=slow)
        if component == "trend":
            return value, value > p["threshold"], details
        previous = float(c[-p["short"] - 1 : -1].mean())
        near = abs(float(rows[-2]["low"]) / previous - 1) <= p["tolerance"]
        details.update(previous_mean=previous, previous_low=rows[-2]["low"], recovered=bool(c[-1] > c[-2]))
        return value, bool(value > 0 and near and c[-1] > max(fast, c[-2])), details
    if component == "macd":
        series = pd.Series(c)
        difference = series.ewm(span=p["fast"], adjust=False).mean() - series.ewm(span=p["slow"], adjust=False).mean()
        signal = difference.ewm(span=p["signal"], adjust=False).mean()
        value = float((difference.iloc[-1] - signal.iloc[-1]) / c[-1])
        details.update(difference=float(difference.iloc[-1]), signal=float(signal.iloc[-1]))
        return value, bool(value > 0 and difference.iloc[-1] > 0), details
    if component == "rsi":
        delta = np.diff(c[-w - 1 :])
        gains, losses = np.maximum(delta, 0).mean(), -np.minimum(delta, 0).mean()
        value = float(100 - 100 / (1 + gains / losses)) if losses else (100.0 if gains else 50.0)
        details["rsi"] = value
        return 1 - value / 100, value <= p["ceiling"], details
    if component == "bollinger":
        mean, std = c[-w - 1 : -1].mean(), c[-w - 1 : -1].std()
        value = float((c[-1] - mean) / (std if std > 0 else mean))
        details.update(mean=float(mean), deviation=float(std), z=value)
        return (
            (-value if p["mode"] == "reversion" else value),
            bool(value < -p["deviations"] if p["mode"] == "reversion" else value > p["deviations"]),
            details,
        )
    if component == "donchian":
        high = max(float(row["high"]) for row in rows[-w - 1 : -1])
        value = float(c[-1] / high - 1)
        details["prior_high"] = high
        return value, value > p["threshold"], details
    if component == "contraction":
        returns = np.diff(c) / c[:-1]
        long = float(returns[-p["long"] - 1 : -1].std())
        short = float(returns[-p["short"] - 1 : -1].std())
        ratio = short / long if long > 0 else float("inf")
        volume_ratio = float(v[-1] / v[-p["long"] - 1 : -1].mean()) if v[-p["long"] - 1 : -1].mean() > 0 else 0.0
        breakout = c[-1] > c[-p["short"] - 1 : -1].max()
        details.update(
            contraction_ratio=ratio if np.isfinite(ratio) else None, volume_ratio=volume_ratio, breakout=bool(breakout)
        )
        return (
            float(c[-1] / c[-p["short"] - 1 : -1].max() - 1),
            bool(ratio <= p["max_ratio"] and volume_ratio >= p["min_volume_ratio"] and breakout),
            details,
        )
    if component == "double_bottom":
        low = np.asarray([float(row["low"]) for row in rows[-w:]])
        confirmation = p["confirmation"]
        pivots = [
            i
            for i in range(confirmation, len(low) - confirmation)
            if low[i] == min(low[i - confirmation : i + confirmation + 1])
        ]
        if len(pivots) < 2:
            return 0.0, False, {**details, "confirmed_pivots": len(pivots)}
        left, right = pivots[-2:]
        neckline = float(max(float(row["high"]) for row in rows[-w:][left : right + 1]))
        similar = abs(low[left] / low[right] - 1) <= p["tolerance"]
        details.update(left_offset=left, right_offset=right, neckline=neckline, confirmation=confirmation)
        return (
            float(c[-1] / neckline - 1),
            bool(similar and right - left >= p["min_separation"] and c[-1] > neckline),
            details,
        )
    raise ValueError(component)


def evaluate(component: str, symbols: list[str], frame: Frame, params: dict[str, Any]) -> dict[str, Observation]:
    results = {}
    defaults = config()["defaults"]
    for symbol in sorted(symbols):
        rows = frame.history.get(symbol, ())
        meta = frame.metadata.get(symbol, {})
        try:
            if not rows or rows[-1]["date"] != frame.as_of:
                raise ValueError("stale")
            if component == "eligibility":
                if params["require_status"] and "tradable" not in meta:
                    raise ValueError("unknown_status")
                amount = float(
                    np.mean(
                        [
                            float(row.get("amount") or float(row["close"]) * float(row.get("volume") or 0))
                            for row in rows[-params["min_bars"] :]
                        ]
                    )
                )
                passed = (
                    len(rows) >= params["min_bars"]
                    and amount >= params["min_amount"]
                    and not meta.get("suspended", False)
                    and not meta.get("is_st", False)
                    and meta.get("tradable", True)
                )
                value, details = (
                    amount,
                    {"average_amount": amount, "observations": len(rows), "status_supplied": "tradable" in meta},
                )
            elif component in {"low_volatility", "regime", "industry"}:
                w = params["window"]
                if len(rows) < w + 1:
                    raise ValueError("history")
                close = np.asarray([float(row["close"]) for row in rows[-w - 1 :]])
                vol = float(np.std(np.diff(close) / close[:-1]) * defaults["annual_periods"] ** 0.5)
                value = -vol if component == "low_volatility" else float(close[-1] / close[0] - 1)
                details = {"annual_volatility": vol, "momentum": float(close[-1] / close[0] - 1)}
                passed = True
                if component == "industry":
                    if not meta.get("sector"):
                        raise ValueError("unknown_sector")
                    details["sector"] = meta["sector"]
            else:
                value, passed, details = _rule(component, rows, params)
            if not np.isfinite(value):
                raise ValueError("finite")
            results[symbol] = Observation(
                symbol, float(value), "pass" if passed else "reject", "rule_pass" if passed else "rule_reject", details
            )
        except (ValueError, KeyError, ZeroDivisionError, IndexError) as exc:
            results[symbol] = Observation(
                symbol,
                None,
                "unknown",
                str(exc) if str(exc) in {"unknown_sector", "unknown_status", "stale"} else "unknown",
            )
    valid = [row for row in results.values() if row.status == "pass"]
    if component == "low_volatility" and valid:
        count = max(1, int(np.ceil(len(valid) * params["percentile"])))
        keep = {row.symbol for row in sorted(valid, key=lambda item: (-float(item.value or 0), item.symbol))[:count]}
        results = {
            s: Observation(s, r.value, r.status if r.status != "pass" or s in keep else "reject", r.reason, r.evidence)
            for s, r in results.items()
        }
    elif component == "regime" and valid:
        average = float(np.mean([r.evidence["momentum"] for r in valid]))
        volatility = float(np.mean([r.evidence["annual_volatility"] for r in valid]))
        allowed = volatility <= params["max_volatility"] and (
            average > defaults["regimes"]["trend_threshold"]
            if params["mode"] == "trend"
            else average <= defaults["regimes"]["trend_threshold"]
        )
        results = {
            s: Observation(
                s,
                r.value,
                ("pass" if allowed else "reject") if r.status == "pass" else r.status,
                r.reason,
                {**r.evidence, "reference": "equal_weight_pool_proxy", "pool_momentum": average},
            )
            for s, r in results.items()
        }
    elif component == "industry" and valid:
        groups: dict[str, list[float]] = {}
        for row in valid:
            groups.setdefault(row.evidence["sector"], []).append(float(row.value or 0))
        keep = set(sorted(groups, key=lambda k: (-float(np.mean(groups[k])), k))[: params["top_groups"]])
        results = {
            s: Observation(
                s,
                r.value,
                r.status if r.status != "pass" or r.evidence["sector"] in keep else "reject",
                r.reason,
                r.evidence,
            )
            for s, r in results.items()
        }
    return results
