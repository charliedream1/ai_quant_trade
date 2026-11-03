"""UTC time helpers used by storage and API responses."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_date() -> str:
    return utc_now().date().isoformat()
