"""One shared OHLCV snapshot per run, with dated metadata and honest source flags."""

import json
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import PROJECT_ROOT, get_settings
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager
from src.data.backtest_history import load_history
from src.engine.backtest.engines import _mock_events_in_range
from src.engine.market.resource_pool import ResourcePoolService
from src.strategy.composition.config import config, fail
from src.strategy.composition.validation import digest


def plan_symbols(plan: dict[str, Any]) -> list[str]:
    symbols = set(plan["universe"]["symbols"])
    for sleeve in plan.get("sleeves", []):
        symbols.update(plan_symbols(sleeve["definition"]))
    return sorted(symbols)


def load_snapshot(payload: dict[str, Any], plan: dict[str, Any], emit, data: Any = None) -> dict[str, Any]:
    cfg = config()
    archive_id = payload.get("snapshot_id")
    root = (get_settings().data_dir / "pipeline_snapshots").resolve()
    if not root.is_relative_to(PROJECT_ROOT.resolve()):
        raise fail("invalid", "snapshot root")
    if archive_id:
        if (
            not isinstance(archive_id, str)
            or len(archive_id) != 64
            or any(c not in "0123456789abcdef" for c in archive_id)
        ):
            raise fail("invalid", "snapshot id")
        path = root / (archive_id[:24] + ".json")
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if digest(snapshot) != archive_id:
            raise fail("invalid", "snapshot digest")
        if payload.get("symbols") and set(payload["symbols"]) - set(snapshot["history"]):
            raise fail("no_history", "archive does not contain the requested universe")
        emit("data", "archive", {"snapshot_id": archive_id, "source": snapshot["source"]})
        return snapshot
    provider = data or DataSourceManager(market=payload["market"])
    symbols = payload.get("symbols") or plan_symbols(plan)
    if payload.get("resource_pool_id"):
        symbols = [row["symbol"] for row in ResourcePoolService(data=provider).list_items(payload["resource_pool_id"])]
    if not symbols or len(symbols) > cfg["defaults"]["max_symbols"]:
        raise fail("invalid", "symbol count")
    pointer = root / (
        "last-"
        + digest({"market": payload["market"], "symbols": sorted(symbols), "source": provider.source_name})[:16]
        + ".json"
    )
    previous = json.loads(pointer.read_text(encoding="utf-8")) if pointer.is_file() else {}
    history = {}
    metadata = {}
    for symbol in sorted(set(symbols)):
        if payload.get("_checkpoint"):
            payload["_checkpoint"]()
        emit("data", symbol, {"status": "started"})
        fetch = getattr(provider, "strategy_snapshot", provider.stock_detail)
        if payload.get("start_date") and payload.get("end_date") and not provider.is_mock:
            detail = load_history(provider, symbol, payload["start_date"], payload["end_date"], "none", warmup=True)
        else:
            detail = fetch(
                symbol, kline_count=cfg["defaults"]["history_bars"], kline_period="daily", price_adjustment="none"
            )
        rows = detail.get("kline") or []
        if provider.is_mock and rows and str(rows[0].get("date") or "").startswith("D-"):
            end = payload.get("end_date") or date.today().isoformat()
            start = pd.bdate_range(end=end, periods=len(rows))[0].date().isoformat()
            rows = [event.to_dict() for event in _mock_events_in_range(symbol, rows, start, end)]
        normalized: list[dict[str, Any]] = []
        for row in rows:
            stamp = str(row.get("date") or row.get("timestamp") or "")[:10]
            try:
                date.fromisoformat(stamp)
            except ValueError:
                continue
            values = {key: float(row[key]) for key in ("open", "high", "low", "close")}
            if (
                min(values.values()) <= 0
                or not np.isfinite(list(values.values())).all()
                or values["high"] < max(values["open"], values["close"])
                or values["low"] > min(values["open"], values["close"])
            ):
                raise fail("invalid", symbol)
            if row.get("volume") is None or not np.isfinite(float(row["volume"])) or float(row["volume"]) < 0:
                raise fail("unavailable", f"{symbol}: missing/invalid volume")
            normalized.append(
                {
                    **values,
                    **{key: row[key] for key in ("trading_status", "corporate_actions") if key in row},
                    "volume": float(row["volume"]),
                    "data_source": row.get("data_source") or provider.source_name,
                    "date": stamp,
                    "timestamp": stamp,
                    **({"amount": float(row["amount"])} if row.get("amount") is not None else {}),
                }
            )
        if not normalized:
            raise fail("no_history", symbol)
        if len({row["date"] for row in normalized}) != len(normalized):
            raise fail("invalid", "duplicate dates")
        history[symbol] = sorted(normalized, key=lambda row: row["date"])
        quote = detail.get("quote") or {}
        sector = detail.get("industry") or quote.get("industry") or quote.get("sector")
        if isinstance(sector, dict):
            sector = sector.get("name") or sector.get("industry")
        if isinstance(sector, str) and sector:
            metadata[symbol] = {"sector": str(sector), "available_at": utc_now_iso(), "source": provider.source_name}
        if isinstance(quote.get("is_stale"), bool):
            item = metadata.setdefault(symbol, {"available_at": utc_now_iso(), "source": provider.source_name})
            item["fresh_quote"] = not quote["is_stale"]
            if quote["is_stale"]:
                item["tradable"] = False
        old = previous.get("metadata", {}).get(symbol)
        if (
            old
            and symbol in metadata
            and {k: v for k, v in old.items() if k != "available_at"}
            == {k: v for k, v in metadata[symbol].items() if k != "available_at"}
        ):
            metadata[symbol]["available_at"] = old["available_at"]
        emit(
            "data",
            symbol,
            {
                "status": "completed",
                "bars": len(normalized),
                "start": normalized[0]["date"],
                "end": normalized[-1]["date"],
            },
        )
    snapshot = {
        "history": history,
        "metadata": metadata,
        "source": provider.source_name,
        "is_mock": bool(provider.is_mock),
        "market": payload["market"],
        "fetched_at": utc_now_iso(),
        "price_adjustment": "none",
        "limitations": [
            "daily_bar_execution_research",
            "corporate_actions_not_included",
            "fixed_universe_survivorship_not_corrected",
        ],
    }
    key = digest(snapshot)
    root.mkdir(parents=True, exist_ok=True)
    if previous and {k: v for k, v in previous.items() if k != "fetched_at"} == {
        k: v for k, v in snapshot.items() if k != "fetched_at"
    }:
        emit("data", "unchanged_snapshot", {"snapshot_id": digest(previous)})
        return previous
    (root / (key[:24] + ".json")).write_text(
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    pointer.write_text(json.dumps(snapshot, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    emit("data", "snapshot", {"snapshot_id": key, "source": snapshot["source"], "is_mock": snapshot["is_mock"]})
    return snapshot
