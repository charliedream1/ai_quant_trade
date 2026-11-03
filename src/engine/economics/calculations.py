"""Deterministic financial periods and ratios; missing values remain unknown."""

import calendar
import math
from datetime import date
from typing import Any

from .config import economics_config


def numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def previous_quarter(period: str) -> str:
    current = date.fromisoformat(period)
    month = current.month - 3
    year = current.year
    if month <= 0:
        month += 12
        year -= 1
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def growth(current: float | None, base: float | None) -> tuple[float | None, str]:
    if current is None or base is None:
        return None, "missing"
    if base <= 0:
        return None, "zero_base" if base == 0 else "loss_base"
    return (current / base - 1) * 100, "available"


def ratio(numerator, denominator, scale=1):
    return (
        numerator / denominator * scale
        if numerator is not None and denominator is not None and denominator > 0
        else None
    )


def statement_index(source: dict, symbol: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for raw in source["rows"]:
        if str(raw.get("SECURITY_CODE") or "") != symbol:
            raise ValueError("Financial statement security does not match the requested company")
        if raw.get("CURRENCY") not in (None, "CNY"):
            raise ValueError("Financial statement currency is incompatible with the CNY contract")
        period = str(raw["REPORT_DATE"])[:10]
        parsed = date.fromisoformat(period)
        if parsed.month not in (3, 6, 9, 12) or parsed.day != calendar.monthrange(parsed.year, parsed.month)[1]:
            raise ValueError("Financial statements must use calendar-quarter endpoints")
        if parsed > date.today():
            raise ValueError("Financial report periods cannot be in the future")
        if period in result and raw != result[period]:
            raise ValueError("Ambiguous financial revisions for the same reporting period")
        result[period] = raw
    return result


def financial_periods(sources: dict[str, dict], symbol: str, financial_industry: bool) -> list[dict]:
    cfg = economics_config()
    indexed = {kind: statement_index(value, symbol) for kind, value in sources.items()}
    dates = sorted({period for rows in indexed.values() for period in rows})
    values: dict[str, dict[str, Any]] = {}
    for period in dates:
        metrics: dict[str, Any] = {}
        origins = {}
        for name, definition in cfg["fields"].items():
            raw = indexed.get(definition["statement"], {}).get(period, {})
            metrics[name] = next(
                (numeric(raw[key]) for key in definition["fields"] if numeric(raw.get(key)) is not None), None
            )
            origins[name] = {
                "statement": definition["statement"],
                "fields": definition["fields"],
                "announcement_date": str(raw.get("NOTICE_DATE") or "")[:10] or None,
            }
        if (
            metrics["consolidated_profit"] is None
            and metrics["total_profit"] is not None
            and metrics["income_tax"] is not None
        ):
            metrics["consolidated_profit"] = metrics["total_profit"] - metrics["income_tax"]
            origins["consolidated_profit"]["calculation"] = "TOTAL_PROFIT - INCOME_TAX"
        if financial_industry:
            metrics.update(gross_margin=None, roe=None)
        values[period] = {
            "report_period": period,
            "metrics": metrics,
            "origins": origins,
            "statuses": {},
            "missing_statements": [kind for kind in cfg["statements"] if period not in indexed.get(kind, {})],
        }
    for period, value in values.items():
        metrics, statuses = value["metrics"], value["statuses"]
        prior_year = str(int(period[:4]) - 1) + period[4:]
        previous = values.get(prior_year, {}).get("metrics", {})
        for field in ("revenue", "profit"):
            metrics[field + "_yoy"], statuses[field + "_yoy"] = growth(metrics[field], previous.get(field))
        metrics["debt_asset_ratio"] = ratio(metrics["liabilities"], metrics["assets"], 100)
        metrics["cash_profit_ratio"] = ratio(metrics["operating_cashflow"], metrics["consolidated_profit"])
        debt = [metrics[key] for key in ("short_loan", "long_loan", "bonds")]
        metrics["known_debt_components"] = (
            sum(x for x in debt if x is not None)
            if any(x is not None for x in debt) and not financial_industry
            else None
        )
        statuses["known_debt_components"] = "partial_components_not_total_interest_debt"
        for field in ("revenue", "profit", "operating_cashflow"):
            prior = values.get(previous_quarter(period), {}).get("metrics", {}).get(field)
            current = metrics[field]
            metrics[field + "_quarter"] = (
                current
                if period[5:7] == "03"
                else current - prior
                if current is not None and prior is not None
                else None
            )
    for period, value in values.items():
        chain, cursor = [], period
        for _ in range(4):
            chain.append(values.get(cursor, {}).get("metrics", {}))
            cursor = previous_quarter(cursor)
        for field in ("revenue", "profit", "operating_cashflow"):
            quarters = [row.get(field + "_quarter") for row in chain]
            value["metrics"][field + "_ttm"] = sum(quarters) if all(x is not None for x in quarters) else None
    return list(values.values())
