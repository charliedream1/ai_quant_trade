"""Calendar gaps, requested coverage, membership timing and real Qlib parity."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.engine.research.factor_monitor import FactorMonitorService
from src.engine.research.monitor_universe import MonitorUniverses


class PriceData:
    source_name = "test-dated-prices"
    is_mock = True

    def __init__(self):
        days = pd.bdate_range("2025-01-01", periods=85).strftime("%Y-%m-%d").tolist()
        rng = np.random.default_rng(42)
        self.history = {}
        for index, symbol in enumerate(["600519", "300750", "000001", "688981", "300124"]):
            prices = 100 * np.cumprod(1 + rng.normal(0.001 * (index + 1), 0.02, len(days)))
            self.history[symbol] = [
                {
                    "date": day,
                    "close": float(price),
                    "open": float(price * 0.99),
                    "high": float(price * 1.02),
                    "low": float(price * 0.98),
                    "volume": 1000 + day_index * (index + 1),
                }
                for day_index, (day, price) in enumerate(zip(days, prices, strict=True))
            ]

    def stock_detail(self, symbol, **kwargs):
        return {"kline": self.history[symbol], "quote": {"name": symbol}}


def test_monitor_uses_dates_and_counts_failed_requests(client):
    data = PriceData()
    data.history["300750"].pop(40)
    service = FactorMonitorService(data=data)
    universe = ",".join([*data.history, "600000"])
    result = service.monitor(universe, persist=False)
    assert result["coverage"]["requested"] == 6
    assert result["coverage"]["loaded"] == 5
    assert result["metrics"][0]["coverage"] == pytest.approx(5 / 6)
    assert result["coverage"]["failures"][0]["symbol"] == "600000"
    row = next(
        item for item in result["ic_history"] if item["factor_key"] == "momentum_20d" and item["date"] == "2025-02-26"
    )
    # This security lacks the observation day; it must not be paired with another date.
    assert row["asset_count"] == 4
    assert row["label_end"] == "2025-03-05"
    values, targets = [], []
    for bars in data.history.values():
        mapping = {item["date"]: item for item in bars}
        if row["date"] not in mapping:
            continue
        index = next(index for index, bar in enumerate(bars) if bar["date"] == row["date"])
        values.append(bars[index]["close"] / bars[index - 20]["close"] - 1)
        targets.append(mapping[row["label_end"]]["close"] / mapping[row["date"]]["close"] - 1)
    assert row["ic"] == pytest.approx(np.corrcoef(values, targets)[0, 1])


def test_monitor_does_not_force_groups_or_use_immature_labels(client):
    data = PriceData()
    service = FactorMonitorService(data=data)
    result = service.monitor("600519,300750,000001", persist=False, as_of="2025-03-01")
    assert result["ic_history"]
    assert not result["quantile_history"]
    assert all(row["label_end"] <= "2025-03-01" for row in result["ic_history"])
    assert all(row["long_short_return"] is None for row in result["metrics"])


def test_membership_version_masks_before_join_and_after_leave(client):
    data = PriceData()
    service = FactorMonitorService(data=data)
    universes = MonitorUniverses(service.repo, data, service._config())
    version = universes.save_memberships(
        {
            "source": "test historical membership",
            "memberships": [
                {"symbol": symbol, "valid_from": "2025-01-01", "valid_to": "2025-02-25" if symbol == "300750" else ""}
                for symbol in data.history
            ],
        }
    )["version"]
    result = service.monitor(persist=False, as_of="2025-04-30", membership_version=version)
    assert result["universe_metadata"]["history_policy"] == "用户提供时点成员"
    assert not any(row["symbol"] == "300750" for row in result["snapshots"])
    assert all(row["asset_count"] == 4 for row in result["ic_history"] if row["date"] > "2025-02-25")


def test_scope_cache_and_alerts_are_isolated(client):
    data = PriceData()
    service = FactorMonitorService(data=data)
    first = service.monitor(",".join(data.history))
    second = service.monitor(",".join(data.history))
    assert not first["cache_hit"] and second["cache_hit"]
    service.monitor("600519,300750,000001")
    assert service.repo.db.scalar("SELECT COUNT(DISTINCT universe) FROM factor_metrics_daily") == 2
    assert service.repo.db.scalar("SELECT COUNT(DISTINCT scope) FROM factor_alerts") == 2


def test_actual_qlib_signal_analysis_matches_builtin(client):
    root = Path(__file__).resolve().parents[2]
    if not (root / ".venv-qlib").is_dir():
        pytest.skip("requires the separately tested Qlib environment")
    data = PriceData()
    service = FactorMonitorService(data=data)
    symbols = ",".join(data.history)
    builtin = service.monitor(symbols, persist=False)
    qlib = service.monitor(symbols, persist=False, backend="qlib")
    assert qlib["backend"] == "qlib"
    assert qlib["qlib"]["status"] == "available"
    left = {(row["factor_key"], row["date"]): row for row in builtin["ic_history"]}
    right = {(row["factor_key"], row["date"]): row for row in qlib["ic_history"]}
    assert left.keys() == right.keys()
    for key in left:
        assert right[key]["ic"] == pytest.approx(left[key]["ic"], abs=1e-10)
        assert right[key]["rank_ic"] == pytest.approx(left[key]["rank_ic"], abs=1e-10)
