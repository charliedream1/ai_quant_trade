"""Account, security and portfolio limits; clipped risk remains cash."""

from copy import deepcopy
from typing import Any

import numpy as np

from src.engine.composition.book import GroupView, PortfolioBook
from src.portfolio.allocation import covariance, returns_panel
from src.strategy.components.rules import atr
from src.strategy.composition.config import config, fail
from src.strategy.composition.contracts import Frame


class RiskManager:
    def __init__(self, params: dict[str, Any], state: dict[str, Any] | None = None):
        self.params = params
        self.state = (
            deepcopy(state)
            if state
            else {
                "peak": 0.0,
                "last_nav": None,
                "freeze_until": -1,
                "drawdown_latched": False,
                "price_peaks": {},
                "cooldowns": {},
            }
        )

    def evaluate(
        self,
        proposed: dict[str, float],
        frame: Frame,
        book: PortfolioBook | GroupView,
        hard_limits: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> tuple[dict[str, float], dict[str, Any]]:
        p = dict(self.params)
        for key, value in (hard_limits or {}).items():
            if key in p and isinstance(value, (float, int)):
                p[key] = min(p[key], value)
        snapshot = book.snapshot()
        nav = snapshot.get("performance_nav", book.nav())
        current = snapshot["weights"]
        self.state["peak"] = max(float(self.state["peak"]), nav, book.capital)
        drawdown = max(0.0, 1 - nav / self.state["peak"]) if self.state["peak"] else 0.0
        previous = self.state["last_nav"]
        if self.state.get("baseline_session") != book.session:
            self.state["baseline_session"] = book.session
            self.state["baseline_nav"] = previous
        baseline = self.state.get("baseline_nav")
        daily = nav / baseline - 1 if baseline and baseline > 0 else 0.0
        events = []
        emergency = set()
        if p["max_drawdown"] and drawdown >= p["max_drawdown"]:
            self.state["drawdown_latched"] = True
        if p["daily_loss"] and daily <= -p["daily_loss"]:
            self.state["freeze_until"] = max(self.state["freeze_until"], book.session + p["cooldown_sessions"])
            events.append({"rule": "daily_loss", "value": daily, "limit": p["daily_loss"]})
        frozen = self.state["drawdown_latched"] or book.session <= self.state["freeze_until"]
        if any(not np.isfinite(weight) or weight < 0 for weight in proposed.values()):
            raise fail("invalid", "target weights")
        targets = {symbol: float(weight) for symbol, weight in proposed.items()}
        for symbol, quantity in book.positions().items():
            price = book.prices[symbol]
            peak = max(self.state["price_peaks"].get(symbol, price), price)
            self.state["price_peaks"][symbol] = peak
            lots = [lot for sleeve in book.sleeves.values() for lot in sleeve.state["lots"].get(symbol, [])]
            entry = sum(lot["price"] * lot["quantity"] for lot in lots) / quantity
            age = book.session - min(lot["open_session"] for lot in lots)
            average_range = atr(frame.history.get(symbol, ()), p["atr_window"])
            checks = {
                "stop_loss": bool(p["stop_loss"] and price <= entry * (1 - p["stop_loss"])),
                "atr_stop": bool(
                    p["atr_multiple"] and average_range > 0 and price <= entry - p["atr_multiple"] * average_range
                ),
                "trailing_stop": bool(p["trailing_stop"] and price <= peak * (1 - p["trailing_stop"])),
                "time_exit": bool(p["max_holding_sessions"] and age >= p["max_holding_sessions"]),
            }
            if any(checks.values()):
                self.state["cooldowns"][symbol] = book.session + p["cooldown_sessions"]
                emergency.add(symbol)
                events.append(
                    {
                        "symbol": symbol,
                        "rule": "exit",
                        "checks": checks,
                        "price": price,
                        "entry": entry,
                        "peak": peak,
                        "age": age,
                        "atr": average_range,
                    }
                )
        for symbol in list(targets):
            meta = frame.metadata.get(symbol, {})
            if (
                symbol not in frame.active()
                or (p["require_tradability"] and "tradable" not in meta)
                or meta.get("suspended")
                or meta.get("is_st")
                or not meta.get("tradable", True)
            ):
                targets[symbol] = min(targets[symbol], current.get(symbol, 0))
                events.append({"symbol": symbol, "rule": "eligibility", "action": "no_increase"})
            if p["require_sector"] and not meta.get("sector"):
                targets[symbol] = min(targets[symbol], current.get(symbol, 0))
                events.append({"symbol": symbol, "rule": "unknown_sector", "action": "no_increase"})
            if p["require_asset_class"] and not meta.get("asset_class"):
                targets[symbol] = min(targets[symbol], current.get(symbol, 0))
                events.append({"symbol": symbol, "rule": "unknown_asset_class", "action": "no_increase"})
            if self.state["cooldowns"].get(symbol, -1) >= book.session:
                targets[symbol] = 0.0
                emergency.add(symbol)
            if frozen:
                targets[symbol] = 0.0
                emergency.add(symbol)
            targets[symbol] = min(targets[symbol], p["max_weight"])
        leaders = sorted(targets, key=lambda s: (-targets[s], s))[: p["max_positions"]]
        targets = {s: (w if s in leaders else 0.0) for s, w in targets.items()}
        for symbol in set(current) - set(targets):
            targets[symbol] = 0.0
        scale = 1.0
        for threshold, multiplier in sorted(p["drawdown_steps"]):
            if drawdown >= threshold:
                scale = min(scale, multiplier)
        total = sum(targets.values())
        if total > 0:
            scale = min(scale, p["max_exposure"] / total)
        targets = {s: w * min(scale, 1) for s, w in targets.items()}
        groups: dict[str, list[str]] = {}
        missing = []
        for symbol in targets:
            sector = frame.metadata.get(symbol, {}).get("sector")
            if sector:
                groups.setdefault(str(sector), []).append(symbol)
            elif targets[symbol] > 0:
                missing.append(symbol)
        for sector, members in groups.items():
            weight = sum(targets[s] for s in members)
            factor = min(1.0, p["max_sector_weight"] / weight) if weight else 1.0
            if factor < 1:
                events.append(
                    {"rule": "sector_limit", "sector": sector, "before": weight, "cap": p["max_sector_weight"]}
                )
                for symbol in members:
                    targets[symbol] *= factor
        asset_groups: dict[str, list[str]] = {}
        for symbol in targets:
            asset_class = frame.metadata.get(symbol, {}).get("asset_class")
            if asset_class:
                asset_groups.setdefault(str(asset_class), []).append(symbol)
        for asset_class, members in asset_groups.items():
            total_weight = sum(targets[s] for s in members)
            if total_weight > p["max_asset_class_weight"]:
                for symbol in members:
                    targets[symbol] *= p["max_asset_class_weight"] / total_weight
                events.append(
                    {
                        "rule": "asset_class_limit",
                        "asset_class": asset_class,
                        "before": total_weight,
                        "cap": p["max_asset_class_weight"],
                    }
                )
        statistics = self._portfolio_risk(targets, frame, p, events)
        if statistics.get("unavailable"):
            targets = {s: min(w, current.get(s, 0)) for s, w in targets.items()}
            events.append({"rule": "covariance_unavailable", "action": "no_increase"})
        if commit:
            self.state["last_nav"] = nav
        return targets, {
            "events": events,
            "emergency": sorted(emergency),
            "frozen": bool(frozen),
            "drawdown": drawdown,
            "daily_return": daily,
            "cash_target": 1 - sum(targets.values()),
            "missing_sector": missing,
            "portfolio": statistics,
            "state": deepcopy(self.state),
        }

    def _portfolio_risk(
        self, targets: dict[str, float], frame: Frame, p: dict[str, Any], events: list
    ) -> dict[str, Any]:
        names = sorted(s for s, w in targets.items() if w > 0)
        if not names:
            return {"annual_volatility": 0.0, "contributions": {}}
        try:
            panel = returns_panel(frame, names, p["covariance_window"], p["min_covariance_observations"])
            matrix = covariance(panel, config()["defaults"]["portfolio"]["shrinkage"])
            correlations = panel.corr().fillna(0).to_numpy()
            remaining = set(range(len(names)))
            while remaining:
                cluster = {min(remaining)}
                while True:
                    expanded = cluster | {
                        j for i in cluster for j in remaining if correlations[i, j] >= p["correlation_threshold"]
                    }
                    if expanded == cluster:
                        break
                    cluster = expanded
                remaining -= cluster
                members = [names[i] for i in sorted(cluster)]
                exposure = sum(targets[s] for s in members)
                if exposure > p["max_cluster_weight"]:
                    for s in members:
                        targets[s] *= p["max_cluster_weight"] / exposure
                    events.append(
                        {
                            "rule": "cluster_limit",
                            "symbols": members,
                            "before": exposure,
                            "cap": p["max_cluster_weight"],
                        }
                    )
            weights = np.asarray([targets[s] for s in names])
            variance = float(weights @ matrix @ weights)
            volatility = float(np.sqrt(max(variance, 0) * config()["defaults"]["annual_periods"]))
            if p["target_volatility"] and volatility > p["target_volatility"]:
                factor = p["target_volatility"] / volatility
                targets.update({s: targets[s] * factor for s in names})
                weights *= factor
                variance = float(weights @ matrix @ weights)
                volatility = p["target_volatility"]
                events.append({"rule": "volatility_scale", "factor": factor})
            contributions = weights * (matrix @ weights) / variance if variance > 0 else np.zeros(len(names))
            return {
                "annual_volatility": volatility,
                "observations": len(panel),
                "contributions": dict(zip(names, map(float, contributions), strict=True)),
            }
        except ValueError as exc:
            events.append({"rule": "covariance_unavailable", "error": str(exc)})
            return {"annual_volatility": None, "contributions": {}, "unavailable": True}
