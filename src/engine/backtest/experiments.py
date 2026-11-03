"""Immutable evidence for a parameter experiment, stored with its backtest task."""

from __future__ import annotations

import hashlib
import json
import platform
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.core.timeutil import utc_now_iso
from src.data.manager import current_market
from src.strategy.ports import MarketEvent

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _dependency_versions(model_profile: str | None) -> dict[str, str]:
    packages = ["numpy", "pandas", "pyyaml"]
    if model_profile:
        packages.extend(["lightgbm", "xgboost", "torch", "scikit-learn"])
    versions = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not_installed"
    return versions


def ohlcv_digest(events: dict[str, list[MarketEvent]]) -> str:
    rows = {
        symbol: [[event.timestamp, event.open, event.high, event.low, event.close, event.volume] for event in values]
        for symbol, values in sorted(events.items())
    }
    return hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def experiment_snapshot(
    resolution: dict[str, Any], payload: dict[str, Any], symbols: list[str], execution: dict[str, Any]
) -> dict[str, Any]:
    files = [
        "egs/execution_costs.yaml",
        "src/engine/backtest/engines.py",
        "src/engine/backtest/runner.py",
        "src/engine/backtest/experiments.py",
        "src/strategy/parameters.py",
        "src/strategy/parameter_profiles.py",
        "src/strategy/loader.py",
        "src/strategy/adapters.py",
    ]
    if resolution.get("model_profile"):
        files.extend(
            path.relative_to(PROJECT_ROOT).as_posix() for path in (PROJECT_ROOT / "src/strategy/models").glob("*.py")
        )
        files.append("egs/model_strategies.yaml")
    files.extend(
        path.relative_to(PROJECT_ROOT).as_posix() for path in (PROJECT_ROOT / "src/engine/execution").glob("*.py")
    )
    files.extend(["src/data/backtest_history.py", "egs/backtest.yaml", "src/engine/backtest/capabilities.py"])
    return deepcopy(
        {
            "schema_version": 1,
            "resolved_at": utc_now_iso(),
            "strategy": {
                **resolution["strategy"],
                "entry": resolution["entry"],
                "source_sha256": hashlib.sha256(resolution["source"].encode("utf-8")).hexdigest(),
            },
            "profile": resolution["profile"],
            "profile_file": resolution["profile_file"],
            "model_profile": resolution["model_profile"],
            "layers": resolution["layers"],
            "resolved_params": resolution["resolved_params"],
            "run": {
                "engine": payload.get("engine"),
                "symbols": list(symbols),
                "start_date": payload["start_date"],
                "end_date": payload["end_date"],
                "initial_capital": payload["initial_capital"],
                "commission_rate": payload["commission_rate"],
                **execution,
            },
            "runtime": {
                "python": platform.python_version(),
                "app_version": get_settings().version,
                "dependencies": _dependency_versions(resolution.get("model_profile")),
            },
            "code_sha256": {
                name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() for name in sorted(files)
            },
            "data": {"mode": get_settings().data_mode, "market": current_market()},
        }
    )


def complete_snapshot(snapshot: dict[str, Any], metrics: dict[str, Any], curve: dict[str, Any]) -> None:
    dates = list(curve.get("dates") or [])
    snapshot["data"].update(
        {
            "source": metrics.get("data_source"),
            "fingerprint": metrics.get("data_fingerprint"),
            "fingerprint_scope": "normalized_ohlcv" if metrics.get("data_fingerprint") else None,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "equity_points": len(dates),
            "bars_by_symbol": metrics.get("bars_by_symbol"),
            "date_coverage": metrics.get("date_coverage"),
        }
    )
