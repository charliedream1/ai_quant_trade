"""Configurable ETF universes and source-backed ETF snapshots."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from src.core.exceptions import BusinessError, ErrorCode
from src.core.timeutil import utc_now_iso

from .manager import DataSourceManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "egs" / "etf_universes.yaml"


class ETFUniverseService:
    """Resolve ETF pools from YAML and retain missing-data states explicitly."""

    def __init__(self, data: DataSourceManager | None = None) -> None:
        self.data = data or DataSourceManager()

    def _payload(self) -> dict[str, Any]:
        payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict) or not isinstance(payload.get("universes"), dict):
            raise BusinessError(ErrorCode.CONFIG_DEPENDENCY, "ETF 配置缺少 universes")
        return payload

    def list_universes(self) -> list[dict[str, Any]]:
        payload = self._payload()
        return [
            {
                "universe": key,
                "label": str(value.get("label") or key),
                "market": str(value.get("market") or "CN"),
                "benchmark": str(value.get("benchmark") or ""),
                "rebalance_frequency": str(value.get("rebalance_frequency") or "monthly"),
                "symbol_count": len(value.get("symbols") or []),
                "asset_type": str(payload.get("asset_type") or "etf"),
            }
            for key, value in payload["universes"].items()
            if isinstance(value, dict)
        ]

    def universe(self, name: str) -> dict[str, Any]:
        key = str(name or "").strip()
        payload = self._payload()
        value = payload["universes"].get(key)
        if not isinstance(value, dict):
            raise BusinessError(ErrorCode.NOT_FOUND, f"ETF池不存在：{key}")
        result = deepcopy(value)
        result["universe"] = key
        result["asset_type"] = str(payload.get("asset_type") or "etf")
        return result

    def symbols(self, name: str) -> list[str]:
        return [str(item.get("symbol")) for item in self.universe(name).get("symbols") or [] if item.get("symbol")]

    def snapshot(self, name: str) -> dict[str, Any]:
        config = self.universe(name)
        rows = []
        for item in config.get("symbols") or []:
            symbol = str(item.get("symbol") or "")
            row = {
                **item,
                "asset_type": "etf",
                "data_source": self.data.source_name,
                "updated_at": utc_now_iso(),
            }
            try:
                detail = self.data.stock_detail(symbol=symbol, kline_count=60, kline_period="daily")
                quote = detail.get("quote") or {}
                kline = detail.get("kline") or []
                row.update(
                    {
                        "latest_price": quote.get("latest_price") or quote.get("price"),
                        "change_pct": quote.get("change_pct"),
                        "average_amount": _average_amount(kline),
                        "history_points": len(kline),
                        "status": "available" if kline else "missing_history",
                        "data_source": quote.get("data_source") or self.data.source_name,
                    }
                )
            except Exception as exc:
                row.update({"status": "unavailable", "error": str(exc), "history_points": 0})
            rows.append(row)
        return {
            "universe": config["universe"],
            "label": config.get("label"),
            "benchmark": config.get("benchmark"),
            "rebalance_frequency": config.get("rebalance_frequency"),
            "asset_type": "etf",
            "symbols": rows,
            "available_count": sum(row.get("status") == "available" for row in rows),
            "missing_count": sum(row.get("status") != "available" for row in rows),
        }


def _average_amount(rows: list[dict[str, Any]]) -> float | None:
    values = []
    for row in rows:
        value = row.get("amount")
        try:
            if value is not None and float(value) > 0:
                values.append(float(value))
        except (TypeError, ValueError):
            continue
    return round(sum(values) / len(values), 2) if values else None
