"""Bounded imports retain publication, availability and revision identities."""

import math
import re
from datetime import date
from typing import Any

from .config import config, digest, invalid
from .pit import timestamp


def validate_dataset(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "market":
        return _market(payload)
    if kind in {"documents", "macro"}:
        return _dated(kind, payload)
    raise invalid("数据类型必须为market、documents或macro")


def _market(payload: dict[str, Any]) -> dict[str, Any]:
    cfg = config()
    history = payload.get("history")
    if not isinstance(history, dict) or not 1 <= len(history) <= cfg["limits"]["max_assets"]:
        raise invalid("行情母池为空或超出证券数量限制")
    normalized = {}
    for symbol, rows in history.items():
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,30}", symbol):
            raise invalid("证券标识不合法")
        if not isinstance(rows, list) or not 2 <= len(rows) <= cfg["limits"]["max_dates"]:
            raise invalid("单证券行情数量不合法")
        output = []
        for row in rows:
            try:
                day = date.fromisoformat(str(row["date"])).isoformat()
                values = {key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}
                if "amount" in row:
                    values["amount"] = float(row["amount"])
            except (KeyError, TypeError, ValueError) as exc:
                raise invalid("行情缺少合法日期/OHLCV字段") from exc
            if (
                not all(math.isfinite(value) for value in values.values())
                or min(values[key] for key in ("open", "high", "low", "close")) <= 0
                or values["volume"] < 0
                or values["high"] < max(values["open"], values["close"])
                or values["low"] > min(values["open"], values["close"])
            ):
                raise invalid("行情数值、价格范围或成交量不合法")
            output.append(
                {
                    "date": day,
                    "timestamp": day,
                    **values,
                    **{key: row[key] for key in ("trading_status", "corporate_actions", "data_source") if key in row},
                }
            )
        if len({row["date"] for row in output}) != len(output):
            raise invalid("同一证券的日期重复")
        normalized[symbol] = sorted(output, key=lambda item: item["date"])
    if len({row["date"] for rows in normalized.values() for row in rows}) > cfg["limits"]["max_dates"]:
        raise invalid("合并交易日历超过研究日期预算")
    if payload.get("market", "CN") not in {"CN", "US"}:
        raise invalid("行情市场标识不合法")
    return {
        "history": normalized,
        "metadata": payload.get("metadata") or {},
        "source": str(payload.get("source") or "user_import"),
        "is_mock": bool(payload.get("is_mock", False)),
        "market": str(payload.get("market") or "CN"),
        "price_adjustment": str(payload.get("price_adjustment") or "unknown"),
        "limitations": list(payload.get("limitations") or ["fixed_universe_survivorship_not_corrected"]),
    }


def _dated(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("documents" if kind == "documents" else "observations")
    if not isinstance(rows, list) or not 1 <= len(rows) <= config()["limits"]["max_documents"]:
        raise invalid("资料为空或超过导入上限")
    output = []
    for raw in rows:
        try:
            row = dict(raw)
            published, available = timestamp(row["published_at"]), timestamp(row["available_at"])
            if published > available:
                raise invalid("可得时点不能早于发布时间")
            row["published_at"], row["available_at"] = published.isoformat(), available.isoformat()
            row["id"] = str(row.get("id") or digest(row))
            if kind == "documents":
                if (
                    not isinstance(row.get("text"), str)
                    or not 1 <= len(row["text"]) <= config()["limits"]["max_document_chars"]
                ):
                    raise invalid("资料正文为空或过长")
                if not isinstance(row.get("symbols"), list) or not row["symbols"]:
                    raise invalid("资料必须有明确的公司证券标识")
                if any(
                    not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,30}", symbol)
                    for symbol in row["symbols"]
                ):
                    raise invalid("资料中的公司证券标识不合法")
            else:
                vintage = timestamp(row["vintage_at"])
                if not published <= vintage <= available:
                    raise invalid("宏观版本时间不合法")
                row["vintage_at"] = vintage.isoformat()
                row["observation_date"] = date.fromisoformat(row["observation_date"]).isoformat()
                if row["observation_date"] > published.date().isoformat():
                    raise invalid("宏观实际观察期不能晚于资料发布日期；预测数据需要单独契约")
                row["value"] = float(row["value"])
                if not math.isfinite(row["value"]) or not isinstance(row["series"], str):
                    raise invalid("宏观值或序列不合法")
            if not row.get("source"):
                raise invalid("资料必须记录来源")
            output.append(row)
        except (TypeError, KeyError, ValueError) as exc:
            raise invalid("资料字段或时间不合法") from exc
    if len({row["id"] for row in output}) != len(output):
        raise invalid("资料ID重复")
    if kind == "macro" and len({(row["series"], row["observation_date"], row["vintage_at"]) for row in output}) != len(
        output
    ):
        raise invalid("同一宏观序列、观察期和修订版本重复")
    return {
        "documents" if kind == "documents" else "observations": output,
        "is_mock": bool(payload.get("is_mock", False)),
        "source": str(payload.get("source") or "user_import"),
    }
