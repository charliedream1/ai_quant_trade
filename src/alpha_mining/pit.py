"""Point-in-time selection and deliberately date-free model observations."""

from datetime import UTC, datetime, timedelta
from typing import Any

from .config import invalid


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise invalid("资料时点必须是包含时区的ISO时间") from exc
    if result.tzinfo is None:
        raise invalid("资料时点不能省略时区")
    return result.astimezone(UTC)


def known_documents(rows: list[dict[str, Any]], cutoff: str) -> list[dict[str, Any]]:
    end = timestamp(cutoff)
    return [row for row in rows if timestamp(row["available_at"]) <= end]


def macro_snapshot(rows: list[dict[str, Any]], cutoff: str, lag_days: int) -> tuple[list[dict], dict]:
    end = timestamp(cutoff) - timedelta(days=lag_days)
    selected: dict[tuple[str, str], dict] = {}
    for row in rows:
        if timestamp(row["available_at"]) > end or timestamp(row["vintage_at"]) > end:
            continue
        key = row["series"], row["observation_date"]
        previous = selected.get(key)
        if previous is None or timestamp(previous["vintage_at"]) < timestamp(row["vintage_at"]):
            selected[key] = row
    periods = sorted({row["observation_date"] for row in selected.values()})
    observations, mapping = [], {}
    for index, row in enumerate(sorted(selected.values(), key=lambda item: (item["observation_date"], item["series"]))):
        evidence_id = f"e{index + 1}"
        observations.append(
            {
                "id": evidence_id,
                "period": periods.index(row["observation_date"]) - len(periods) + 1,
                "series": row["series"],
                "value": row["value"],
            }
        )
        mapping[evidence_id] = {"id": row["id"], "available_at": row["available_at"], "vintage_at": row["vintage_at"]}
    return observations, mapping
