"""Validate capabilities against the actual snapshot before any execution."""

from typing import Any

from src.strategy.composition.config import fail


def preflight(plan: dict[str, Any], snapshot: dict[str, Any], request: dict[str, Any]) -> list[str]:
    warnings = list(snapshot.get("limitations") or [])
    history = snapshot["history"]
    if request.get("require_real") and snapshot["is_mock"]:
        raise fail("unavailable", "mock source")
    if request["market"] != snapshot["market"]:
        raise fail("invalid", "snapshot market")

    def inspect(value):
        symbols = set(value["universe"]["symbols"]) & set(history) or set(history)
        requires_sector = value["risk"]["require_sector"] or any(n["component"] == "industry" for n in value["nodes"])
        if requires_sector:
            cutoff = str(
                request.get("start_date") if request["mode"] in {"backtest", "replay"} else request["end_date"]
            )
            missing = [
                s
                for s in symbols
                if not snapshot.get("metadata", {}).get(s, {}).get("sector")
                or str(snapshot["metadata"][s].get("available_at", "9999"))[:10] > cutoff
            ]
            if missing:
                raise fail("unknown_sector", ",".join(sorted(missing)))
        elif request["mode"] in {"backtest", "replay"} and any(
            not snapshot.get("metadata", {}).get(s, {}).get("sector")
            or str(snapshot["metadata"][s].get("available_at", "9999"))[:10] > request["start_date"]
            for s in symbols
        ):
            warnings.append("historical_sector_unavailable")
        if any(n["kind"] == "scorer" and n["component"] in {"lightgbm", "xgboost", "mlp"} for n in value["nodes"]):
            calendars = [
                tuple(row["date"] for row in history[s] if row["date"] <= request["end_date"]) for s in sorted(symbols)
            ]
            if len(set(calendars)) > 1:
                raise fail("invalid", "model mother universe requires aligned dates")
        for child in value["sleeves"]:
            inspect(child["definition"])

    inspect(plan)
    return warnings
