"""Trading calendar refresh helpers for scheduled jobs."""

from __future__ import annotations

import html
import importlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import yaml
from loguru import logger

from src.core.config import get_settings
from src.core.timeutil import utc_now_iso

DEFAULT_MARKET = "cn_stock"
DEFAULT_TIMEZONE = "Asia/Shanghai"
AKSHARE_SINA_SOURCE = "akshare_sina"
INLINE_SOURCE = "inline"
DEFAULT_CALENDAR_WARN_DAYS = 14
DEFAULT_CALENDAR_STALE_DAYS = 14
DEFAULT_CALENDAR_DIFF_LIMIT = 20
DEFAULT_ANNOUNCEMENT_URL_TIMEOUT_SECONDS = 10
DEFAULT_ANNOUNCEMENT_URL_MAX_BYTES = 2_000_000
DEFAULT_ANNOUNCEMENT_DISCOVERY_LIMIT = 5
DEFAULT_ANNOUNCEMENT_USER_AGENT = "AllInOneQuantCalendar/1.0"
HOLIDAY_KEYWORDS = ("休市", "不交易", "非交易日", "暂停交易", "暂停服务", "不提供交易", "闭市")
TRADING_KEYWORDS = ("照常开市", "正常开市", "恢复交易", "补班交易", "补充交易", "临时开市")
ANNOUNCEMENT_LINK_KEYWORDS = ("休市", "交易安排", "节假日", "放假", "开市", "交易日", "日历")
ANNOUNCEMENT_DATE_TOKEN = r"(?:20\d{2}\s*(?:年|-|/|\.)\s*)?\d{1,2}\s*(?:月|-|/|\.)\s*\d{1,2}\s*日?"
ANNOUNCEMENT_RANGE_PATTERN = re.compile(
    rf"(?P<start>{ANNOUNCEMENT_DATE_TOKEN})\s*(?:（[^）]*）|\([^)]*\))?\s*(?:至|到|—|－|~)\s*"
    rf"(?P<end>{ANNOUNCEMENT_DATE_TOKEN})"
)
ANNOUNCEMENT_DATE_PATTERN = re.compile(ANNOUNCEMENT_DATE_TOKEN)
ANNOUNCEMENT_LINK_PATTERN = re.compile(
    r"<a\b[^>]*href=[\"'](?P<href>[^\"']+)[\"'][^>]*>(?P<label>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class CalendarRefreshResult:
    path: Path
    market: str
    source: str
    range_start: str
    range_end: str
    trading_day_count: int
    holiday_count: int
    weekend_trading_day_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "market": self.market,
            "source": self.source,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "trading_day_count": self.trading_day_count,
            "holiday_count": self.holiday_count,
            "weekend_trading_day_count": self.weekend_trading_day_count,
        }


@dataclass(frozen=True)
class CalendarReferenceResult:
    path: Path
    market: str
    source: str
    range_start: str
    range_end: str
    holiday_count: int
    weekend_trading_day_count: int
    parsed_from_announcement: bool = False
    announcement_date_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "market": self.market,
            "source": self.source,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "holiday_count": self.holiday_count,
            "weekend_trading_day_count": self.weekend_trading_day_count,
            "parsed_from_announcement": self.parsed_from_announcement,
            "announcement_date_count": self.announcement_date_count,
        }


def refresh_trading_calendar(params: dict[str, Any]) -> CalendarRefreshResult:
    """Refresh and persist a compact YAML trading calendar."""

    market = _market_from_params(params)
    source = _source_from_params(params)
    trade_dates = _trade_dates_from_source(source, params)
    if not trade_dates:
        raise ValueError("交易日历数据为空，无法更新。")
    range_start = _date_param(params, "range_start") or _date_param(params, "start_date") or min(trade_dates)
    range_end = _date_param(params, "range_end") or _date_param(params, "end_date") or max(trade_dates)
    if range_start > range_end:
        raise ValueError("交易日历 range_start 不能晚于 range_end。")

    trade_date_set = {item for item in trade_dates if range_start <= item <= range_end}
    if not trade_date_set:
        raise ValueError("指定区间内没有交易日数据。")

    write_full = _bool_param(params, "write_full_trading_days", False)
    holidays, weekend_trading_days = _compact_calendar_dates(range_start, range_end, trade_date_set)
    trading_days = sorted(item.isoformat() for item in trade_date_set) if write_full else weekend_trading_days
    target_path = _calendar_write_path(params)
    payload = _load_calendar_yaml(target_path)
    markets = payload.setdefault("markets", {})
    if not isinstance(markets, dict):
        markets = {}
        payload["markets"] = markets
    markets[market] = {
        "source": source,
        "timezone": str(params.get("timezone") or DEFAULT_TIMEZONE),
        "updated_at": utc_now_iso(),
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "holidays": holidays,
        "trading_days": trading_days,
        "metadata": {
            "trading_day_count": len(trade_date_set),
            "weekday_holiday_count": len(holidays),
            "weekend_trading_day_count": len(weekend_trading_days),
            "compact": not write_full,
        },
    }
    payload.setdefault("file_format", "yaml")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return CalendarRefreshResult(
        path=target_path,
        market=market,
        source=source,
        range_start=range_start.isoformat(),
        range_end=range_end.isoformat(),
        trading_day_count=len(trade_date_set),
        holiday_count=len(holidays),
        weekend_trading_day_count=len(weekend_trading_days),
    )


def refresh_official_trading_calendar(params: dict[str, Any]) -> CalendarReferenceResult:
    """Persist an official-reference calendar maintained from exchange announcements."""

    market = _market_from_params(params)
    announcement_params = _announcement_params_with_profile(params)
    announcement_index_urls = _announcement_index_urls_from_params(announcement_params)
    discovered_urls = _discover_announcement_urls(announcement_params, announcement_index_urls)
    announcement_urls = _dedupe_urls([*_announcement_urls_from_params(announcement_params), *discovered_urls])
    announcement_text = _announcement_text_from_params(announcement_params, announcement_urls)
    parsed_holidays, parsed_trading_days = (
        _parse_announcement_calendar(announcement_text, params) if announcement_text else ([], [])
    )
    default_source = (
        "official-announcement-discovery"
        if discovered_urls
        else "official-announcement-url"
        if announcement_urls
        else "official-announcement-parser"
        if announcement_text
        else "official-announcement-manual"
    )
    source = str(
        announcement_params.get("official_source")
        or announcement_params.get("reference_source")
        or announcement_params.get("source")
        or default_source
    ).strip()
    holidays = sorted(
        {_parse_date(item).isoformat() for item in [*_list_value(params.get("holidays")), *parsed_holidays]}
    )
    trading_days = sorted(
        {
            _parse_date(item).isoformat()
            for item in [
                *_list_value(
                    params.get("trading_days") or params.get("extra_trading_days") or params.get("weekend_trading_days")
                ),
                *parsed_trading_days,
            ]
        }
    )
    explicit_start = _date_param(params, "range_start") or _date_param(params, "start_date")
    explicit_end = _date_param(params, "range_end") or _date_param(params, "end_date")
    known_dates = [_parse_date(item) for item in holidays + trading_days]
    if explicit_start is None and known_dates:
        explicit_start = min(known_dates)
    if explicit_end is None and known_dates:
        explicit_end = max(known_dates)
    if explicit_start is None or explicit_end is None:
        raise ValueError("官方参考日历需要 range_start/range_end，或提供 holidays/trading_days 日期。")
    if explicit_start > explicit_end:
        raise ValueError("官方参考日历 range_start 不能晚于 range_end。")

    target_path = _official_calendar_write_path(params)
    payload = _load_calendar_yaml(target_path)
    markets = payload.setdefault("markets", {})
    if not isinstance(markets, dict):
        markets = {}
        payload["markets"] = markets
    markets[market] = {
        "source": source,
        "timezone": str(params.get("timezone") or DEFAULT_TIMEZONE),
        "updated_at": utc_now_iso(),
        "range_start": explicit_start.isoformat(),
        "range_end": explicit_end.isoformat(),
        "holidays": holidays,
        "trading_days": trading_days,
        "metadata": {
            "compact": True,
            "official_reference": True,
            "source_note": str(params.get("source_note") or params.get("announcement_title") or ""),
            "parsed_from_announcement": bool(announcement_text),
            "announcement_date_count": len(parsed_holidays) + len(parsed_trading_days),
            "announcement_urls": announcement_urls,
            "announcement_index_urls": announcement_index_urls,
        },
    }
    payload.setdefault("file_format", "yaml")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return CalendarReferenceResult(
        path=target_path,
        market=market,
        source=source,
        range_start=explicit_start.isoformat(),
        range_end=explicit_end.isoformat(),
        holiday_count=len(holidays),
        weekend_trading_day_count=len(trading_days),
        parsed_from_announcement=bool(announcement_text),
        announcement_date_count=len(parsed_holidays) + len(parsed_trading_days),
    )


def validate_announcement_profiles(params: dict[str, Any]) -> dict[str, Any]:
    """Check whether exchange announcement source profiles are still reachable."""

    profile_path = _announcement_profiles_path(params)
    profiles = _announcement_profiles_from_path(profile_path)
    profile_names = _announcement_profile_names_from_params(params, profiles)
    profile_results = [
        _validate_announcement_profile(name, profiles[name], params)
        for name in profile_names
        if isinstance(profiles.get(name), dict)
    ]
    error_count = sum(1 for item in profile_results if item["status"] == "error")
    warning_count = sum(1 for item in profile_results if item["status"] == "warning")
    return {
        "status": "error" if error_count else "warning" if warning_count else "ok",
        "profile_path": str(profile_path),
        "profile_count": len(profiles),
        "checked_profile_count": len(profile_results),
        "ok_count": sum(1 for item in profile_results if item["status"] == "ok"),
        "warning_count": warning_count,
        "error_count": error_count,
        "profiles": profile_results,
    }


def trading_calendar_status(params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a lightweight status summary for the configured trading calendar."""

    params = params or {}
    market = _market_from_params(params)
    path = _calendar_status_path(params)
    if not path.exists():
        return {"status": "missing", "path": str(path), "market": market, "message": "交易日历文件不存在。"}
    try:
        payload = _load_calendar_yaml(path)
        markets = payload.get("markets", {})
        calendar = markets.get(market) if isinstance(markets, dict) else None
        if not isinstance(calendar, dict):
            return {
                "status": "missing_market",
                "path": str(path),
                "market": market,
                "message": f"交易日历文件中缺少市场 {market}。",
            }
        updated_at = str(calendar.get("updated_at") or "")
        return {
            "status": "ok",
            "path": str(path),
            "market": market,
            "source": calendar.get("source") or "",
            "updated_at": updated_at,
            "range_start": calendar.get("range_start") or "",
            "range_end": calendar.get("range_end") or "",
            "holiday_count": len(_list_value(calendar.get("holidays"))),
            "trading_day_count": len(_list_value(calendar.get("trading_days"))),
            "metadata": calendar.get("metadata") if isinstance(calendar.get("metadata"), dict) else {},
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "path": str(path), "market": market, "message": str(exc)}


def trading_calendar_diff(
    params: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare the active calendar with an optional official reference calendar."""

    params = params or {}
    reference_path = _reference_calendar_path(params)
    if reference_path is None:
        return {"status": "not_configured", "message": "未配置官方参考交易日历。"}
    calendar = status or trading_calendar_status(params)
    if calendar.get("status") != "ok":
        return {
            "status": "skipped",
            "message": "当前交易日历不可用，已跳过官方参考差异核验。",
            "calendar_status": calendar.get("status"),
        }
    if not reference_path.exists():
        return {
            "status": "missing_reference",
            "path": str(reference_path),
            "message": "官方参考交易日历文件不存在。",
        }
    try:
        market = _market_from_params(params)
        current_payload = _load_calendar_yaml(Path(str(calendar.get("path"))))
        reference_payload = _load_calendar_yaml(reference_path)
        current_calendar = _calendar_for_market(current_payload, market)
        reference_calendar = _calendar_for_market(reference_payload, market)
        if current_calendar is None:
            return {"status": "missing_market", "path": str(calendar.get("path")), "market": market}
        if reference_calendar is None:
            return {"status": "missing_reference_market", "path": str(reference_path), "market": market}
        window = _diff_window(params, current_calendar, reference_calendar)
        if window is None:
            return {
                "status": "range_missing",
                "path": str(reference_path),
                "market": market,
                "message": "当前日历或官方参考日历缺少可比较的覆盖区间。",
            }
        start, end = window
        current_trade_dates = _calendar_trade_dates(current_calendar, start, end)
        reference_trade_dates = _calendar_trade_dates(reference_calendar, start, end)
        missing_trading_days = sorted(reference_trade_dates - current_trade_dates)
        extra_trading_days = sorted(current_trade_dates - reference_trade_dates)
        limit = _int_param(params, "calendar_diff_limit", DEFAULT_CALENDAR_DIFF_LIMIT)
        return {
            "status": "mismatch" if missing_trading_days or extra_trading_days else "match",
            "path": str(calendar.get("path")),
            "reference_path": str(reference_path),
            "market": market,
            "range_start": start.isoformat(),
            "range_end": end.isoformat(),
            "missing_trading_days": [item.isoformat() for item in missing_trading_days[:limit]],
            "extra_trading_days": [item.isoformat() for item in extra_trading_days[:limit]],
            "missing_trading_day_count": len(missing_trading_days),
            "extra_trading_day_count": len(extra_trading_days),
            "truncated": len(missing_trading_days) > limit or len(extra_trading_days) > limit,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "path": str(reference_path),
            "message": f"官方参考交易日历差异核验失败：{exc}",
        }


def trading_calendar_alerts(
    params: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build operational alerts for the configured trading calendar."""

    params = params or {}
    calendar = status or trading_calendar_status(params)
    calendar_status = str(calendar.get("status") or "unknown")
    base = {
        "source": "trading_calendar",
        "calendar_status": calendar_status,
        "market": calendar.get("market") or _market_from_params(params),
        "path": calendar.get("path") or str(_calendar_status_path(params)),
    }
    if calendar_status != "ok":
        return [
            {
                **base,
                "severity": "critical",
                "code": f"calendar_{calendar_status}",
                "title": "交易日历不可用",
                "message": str(calendar.get("message") or "交易日历无法读取，请检查配置或执行日历更新任务。"),
            }
        ]

    alerts: list[dict[str, Any]] = []
    today = _date_param(params, "as_of_date") or date.today()
    warn_days = _int_param(params, "calendar_warn_days", DEFAULT_CALENDAR_WARN_DAYS)
    stale_days = _int_param(params, "calendar_stale_days", DEFAULT_CALENDAR_STALE_DAYS)
    range_end = _optional_date(calendar.get("range_end"))
    if range_end is None:
        alerts.append(
            {
                **base,
                "severity": "warning",
                "code": "calendar_range_missing",
                "title": "交易日历缺少覆盖区间",
                "message": "交易日历未记录 range_end，交易日过滤无法判断日历是否过期。",
            }
        )
    else:
        days_left = (range_end - today).days
        if days_left < 0:
            alerts.append(
                {
                    **base,
                    "severity": "critical",
                    "code": "calendar_expired",
                    "title": "交易日历已过期",
                    "message": f"交易日历覆盖到 {range_end.isoformat()}，已早于当前日期 {today.isoformat()}。",
                    "days_left": days_left,
                }
            )
        elif days_left <= warn_days:
            alerts.append(
                {
                    **base,
                    "severity": "warning",
                    "code": "calendar_expiring",
                    "title": "交易日历即将过期",
                    "message": f"交易日历覆盖到 {range_end.isoformat()}，剩余 {days_left} 天，请安排更新。",
                    "days_left": days_left,
                }
            )

    updated_at = _optional_datetime(calendar.get("updated_at"))
    if updated_at is None:
        alerts.append(
            {
                **base,
                "severity": "warning",
                "code": "calendar_updated_at_missing",
                "title": "交易日历缺少更新时间",
                "message": "交易日历未记录 updated_at，无法确认最近一次自动更新是否成功。",
            }
        )
    elif stale_days > 0:
        age_days = (
            (datetime.now(updated_at.tzinfo) - updated_at).days
            if updated_at.tzinfo
            else (datetime.now() - updated_at).days
        )
        if age_days > stale_days:
            alerts.append(
                {
                    **base,
                    "severity": "warning",
                    "code": "calendar_stale",
                    "title": "交易日历更新偏久",
                    "message": f"交易日历最近更新时间已超过 {age_days} 天，请确认自动更新任务是否正常。",
                    "age_days": age_days,
                }
            )
    diff = trading_calendar_diff(params, status=calendar)
    if diff.get("status") == "mismatch":
        missing_count = int(diff.get("missing_trading_day_count") or 0)
        extra_count = int(diff.get("extra_trading_day_count") or 0)
        alerts.append(
            {
                **base,
                "severity": "critical",
                "code": "calendar_official_diff",
                "title": "交易日历与官方参考不一致",
                "message": (
                    f"当前交易日历与官方参考在 {diff.get('range_start')} 至 {diff.get('range_end')} "
                    f"存在差异：遗漏交易日 {missing_count} 个，额外交易日 {extra_count} 个。"
                ),
                "diff": diff,
            }
        )
    elif diff.get("status") in {"missing_reference", "missing_reference_market", "range_missing", "error"}:
        alerts.append(
            {
                **base,
                "severity": "warning",
                "code": f"calendar_official_{diff.get('status')}",
                "title": "官方参考日历核验不可用",
                "message": str(diff.get("message") or "官方参考交易日历无法完成差异核验。"),
                "diff": diff,
            }
        )
    return alerts


def _announcement_params_with_profile(params: dict[str, Any]) -> dict[str, Any]:
    profile = _announcement_profile_from_params(params)
    if not profile:
        return params
    return _merge_announcement_profile_params(profile, params)


def _merge_announcement_profile_params(profile: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(profile)
    for key, value in params.items():
        if value in (None, "", [], {}):
            continue
        merged[key] = value
    return merged


def _announcement_profile_from_params(params: dict[str, Any]) -> dict[str, Any]:
    profile_name = str(
        params.get("announcement_profile")
        or params.get("announcement_source_profile")
        or params.get("official_announcement_profile")
        or ""
    ).strip()
    if not profile_name:
        return {}
    profile_path = _announcement_profiles_path(params)
    profiles = _announcement_profiles_from_path(profile_path)
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        raise ValueError(f"官方公告来源 profile 不存在：{profile_name}")
    return dict(profile)


def _announcement_profiles_path(params: dict[str, Any]) -> Path:
    raw = (
        params.get("announcement_profiles_path")
        or params.get("announcement_profile_path")
        or params.get("official_announcement_profiles_path")
        or params.get("official_announcement_profile_path")
        or "egs/exchange_announcement_profiles.yaml"
    )
    path = Path(str(raw))
    resolved = path if path.is_absolute() else (get_settings().project_root / path)
    resolved = resolved.resolve()
    _ensure_project_path(resolved)
    return resolved


def _announcement_profiles_from_path(profile_path: Path) -> dict[str, Any]:
    if not profile_path.exists():
        raise ValueError(f"官方公告来源 profile 文件不存在：{profile_path}")
    payload = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"官方公告来源 profile 文件格式错误：{profile_path}")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError(f"官方公告来源 profile 文件缺少 profiles：{profile_path}")
    return {str(key): value for key, value in profiles.items()}


def _announcement_profile_names_from_params(params: dict[str, Any], profiles: dict[str, Any]) -> list[str]:
    raw = (
        params.get("announcement_profiles")
        or params.get("announcement_profile")
        or params.get("announcement_source_profile")
        or params.get("official_announcement_profile")
    )
    names = [str(item).strip() for item in _list_value(raw) if str(item).strip()]
    if not names:
        return sorted(profiles)
    missing = [name for name in names if name not in profiles]
    if missing:
        raise ValueError(f"官方公告来源 profile 不存在：{', '.join(missing)}")
    return names


def _validate_announcement_profile(name: str, profile: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    profile_params = _merge_announcement_profile_params(profile, params)
    check_limit = _int_param(
        profile_params,
        "announcement_profile_check_limit",
        _int_param(profile_params, "announcement_discovery_limit", DEFAULT_ANNOUNCEMENT_DISCOVERY_LIMIT),
    )
    min_links = max(0, _int_param(profile_params, "announcement_profile_min_links", 1))
    keywords = _announcement_link_keywords(profile_params)
    index_urls = _announcement_index_urls_from_params(profile_params)
    explicit_urls = _announcement_urls_from_params(profile_params)
    index_results: list[dict[str, Any]] = []
    explicit_results: list[dict[str, Any]] = []
    candidate_urls: list[str] = []
    error_count = 0

    for index_url in index_urls:
        try:
            index_html = _download_announcement_text(index_url, profile_params)
            links = _extract_announcement_links(index_html, index_url, keywords, check_limit)
            candidate_urls.extend(links)
            index_results.append(
                {
                    "url": index_url,
                    "status": "ok",
                    "matched_link_count": len(links),
                    "sample_links": links[: min(len(links), 5)],
                }
            )
        except Exception as exc:  # noqa: BLE001
            error_count += 1
            logger.warning("交易所公告源 profile 核验失败：profile={} url={} error={}", name, index_url, exc)
            index_results.append({"url": index_url, "status": "error", "error": str(exc)})

    explicit_check_urls = explicit_urls[: max(0, check_limit)] if check_limit else explicit_urls
    for explicit_url in explicit_check_urls:
        try:
            _download_announcement_text(explicit_url, profile_params)
            explicit_results.append({"url": explicit_url, "status": "ok"})
            candidate_urls.append(explicit_url)
        except Exception as exc:  # noqa: BLE001
            error_count += 1
            logger.warning("交易所公告 URL 核验失败：profile={} url={} error={}", name, explicit_url, exc)
            explicit_results.append({"url": explicit_url, "status": "error", "error": str(exc)})

    candidate_urls = _dedupe_urls(candidate_urls)
    warnings: list[str] = []
    if not index_urls and not explicit_urls:
        error_count += 1
        warnings.append("profile 未配置公告列表页或公告 URL。")
    if len(candidate_urls) < min_links:
        warnings.append(f"候选公告链接数量 {len(candidate_urls)} 少于阈值 {min_links}。")
    if error_count:
        status = "error" if len(candidate_urls) == 0 else "warning"
    else:
        status = "warning" if warnings else "ok"
    return {
        "name": name,
        "label": str(profile.get("label") or name),
        "status": status,
        "index_url_count": len(index_urls),
        "explicit_url_count": len(explicit_urls),
        "candidate_url_count": len(candidate_urls),
        "error_count": error_count,
        "warnings": warnings,
        "keywords": keywords,
        "index_results": index_results,
        "explicit_results": explicit_results,
        "sample_candidate_urls": candidate_urls[: min(len(candidate_urls), 10)],
    }


def _announcement_index_urls_from_params(params: dict[str, Any]) -> list[str]:
    raw = (
        params.get("announcement_index_url")
        or params.get("announcement_index_urls")
        or params.get("official_announcement_index_url")
        or params.get("official_announcement_index_urls")
    )
    urls: list[str] = []
    for value in _list_value(raw):
        url = str(value).strip()
        if not url:
            continue
        _validate_announcement_url(url)
        urls.append(url)
    return _dedupe_urls(urls)


def _discover_announcement_urls(params: dict[str, Any], index_urls: list[str]) -> list[str]:
    if not index_urls:
        return []
    limit = _int_param(params, "announcement_discovery_limit", DEFAULT_ANNOUNCEMENT_DISCOVERY_LIMIT)
    if limit <= 0:
        return []
    keywords = _announcement_link_keywords(params)
    discovered: list[str] = []
    for index_url in index_urls:
        index_html = _download_announcement_text(index_url, params)
        discovered.extend(_extract_announcement_links(index_html, index_url, keywords, limit - len(discovered)))
        if len(discovered) >= limit:
            break
    return _dedupe_urls(discovered)[:limit]


def _announcement_link_keywords(params: dict[str, Any]) -> list[str]:
    raw = params.get("announcement_link_keywords")
    if raw in (None, ""):
        return list(ANNOUNCEMENT_LINK_KEYWORDS)
    return [str(item).strip() for item in _list_value(raw) if str(item).strip()]


def _extract_announcement_links(html_text: str, base_url: str, keywords: list[str], limit: int) -> list[str]:
    if limit <= 0:
        return []
    links: list[str] = []
    for match in ANNOUNCEMENT_LINK_PATTERN.finditer(html_text):
        href = html.unescape(match.group("href")).strip()
        label = _strip_html_text(match.group("label"))
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        candidate_text = f"{label} {href}"
        if keywords and not any(keyword in candidate_text for keyword in keywords):
            continue
        url = urljoin(base_url, href)
        try:
            _validate_announcement_url(url)
        except ValueError:
            continue
        links.append(url)
        if len(links) >= limit:
            break
    return _dedupe_urls(links)


def _strip_html_text(text: str) -> str:
    normalized = html.unescape(text)
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    return unique_urls


def _announcement_text_from_params(params: dict[str, Any], announcement_urls: list[str] | None = None) -> str:
    chunks: list[str] = []
    for key in ("announcement_text", "announcement_html", "official_announcement", "announcement"):
        value = params.get(key)
        if value not in (None, ""):
            chunks.append(str(value))
    path = _announcement_path(params)
    if path is not None:
        if not path.exists():
            raise ValueError(f"官方公告文件不存在：{path}")
        encoding = str(params.get("announcement_encoding") or "utf-8")
        chunks.append(path.read_text(encoding=encoding))
    for url in announcement_urls or []:
        chunks.append(_download_announcement_text(url, params))
    return "\n".join(item.strip() for item in chunks if item.strip())


def _announcement_urls_from_params(params: dict[str, Any]) -> list[str]:
    raw = (
        params.get("announcement_url")
        or params.get("announcement_urls")
        or params.get("official_announcement_url")
        or params.get("official_announcement_urls")
    )
    urls: list[str] = []
    for value in _list_value(raw):
        url = str(value).strip()
        if not url:
            continue
        _validate_announcement_url(url)
        urls.append(url)
    return urls


def _validate_announcement_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"官方公告 URL 仅支持 http/https：{url}")


def _download_announcement_text(url: str, params: dict[str, Any]) -> str:
    timeout = _int_param(params, "announcement_url_timeout_seconds", DEFAULT_ANNOUNCEMENT_URL_TIMEOUT_SECONDS)
    max_bytes = _int_param(params, "announcement_url_max_bytes", DEFAULT_ANNOUNCEMENT_URL_MAX_BYTES)
    if max_bytes <= 0:
        raise ValueError("announcement_url_max_bytes 必须大于 0。")
    user_agent = str(params.get("announcement_user_agent") or DEFAULT_ANNOUNCEMENT_USER_AGENT)
    request = Request(url, headers={"User-Agent": user_agent})
    logger.info("读取官方公告 URL：{}", url)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError(f"官方公告 URL 内容超过限制：{url}")
        charset = response.headers.get_content_charset() if response.headers else None
    return _decode_announcement_bytes(raw, str(params.get("announcement_encoding") or charset or ""))


def _decode_announcement_bytes(raw: bytes, preferred_encoding: str = "") -> str:
    encodings = [item for item in (preferred_encoding, "utf-8-sig", "utf-8", "gb18030") if item]
    seen: set[str] = set()
    for encoding in encodings:
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode(preferred_encoding or "utf-8", errors="replace")


def _announcement_path(params: dict[str, Any]) -> Path | None:
    raw = (
        params.get("announcement_path")
        or params.get("announcement_file")
        or params.get("official_announcement_path")
        or params.get("official_announcement_file")
    )
    if raw in (None, ""):
        return None
    path = Path(str(raw))
    resolved = path if path.is_absolute() else (get_settings().project_root / path)
    resolved = resolved.resolve()
    _ensure_project_path(resolved)
    return resolved


def _parse_announcement_calendar(text: str, params: dict[str, Any]) -> tuple[list[str], list[str]]:
    default_year = _announcement_default_year(params, text)
    holidays: set[date] = set()
    trading_days: set[date] = set()
    for segment in _announcement_segments(text):
        for clause in _announcement_clauses(segment):
            dates = _announcement_dates_from_clause(clause, default_year)
            if not dates:
                continue
            if _is_announcement_holiday_clause(clause):
                holidays.update(item for item in dates if item.weekday() < 5)
            if _is_announcement_trading_clause(clause):
                trading_days.update(item for item in dates if item.weekday() >= 5)
    return sorted(item.isoformat() for item in holidays), sorted(item.isoformat() for item in trading_days)


def _announcement_default_year(params: dict[str, Any], text: str) -> int:
    for key in ("announcement_year", "calendar_year", "year"):
        value = params.get(key)
        if value not in (None, ""):
            return int(str(value))
    explicit_start = _date_param(params, "range_start") or _date_param(params, "start_date")
    if explicit_start is not None:
        return explicit_start.year
    match = re.search(r"20\d{2}", text)
    if match:
        return int(match.group(0))
    return date.today().year


def _announcement_segments(text: str) -> list[str]:
    normalized = html.unescape(text)
    normalized = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", normalized)
    normalized = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6])\s*>", "。\n", normalized)
    normalized = re.sub(r"<[^>]+>", " ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return [item.strip() for item in re.split(r"[。\n\r；;]+", normalized) if item.strip()]


def _announcement_clauses(segment: str) -> list[str]:
    return [item.strip() for item in re.split(r"[，,]+", segment) if item.strip()]


def _announcement_dates_from_clause(clause: str, default_year: int) -> set[date]:
    dates: set[date] = set()
    for match in ANNOUNCEMENT_RANGE_PATTERN.finditer(clause):
        try:
            start = _parse_announcement_date_token(match.group("start"), default_year)
            end_default_year = start.year if not _announcement_token_has_year(match.group("end")) else default_year
            end = _parse_announcement_date_token(match.group("end"), end_default_year)
            if end < start and not _announcement_token_has_year(match.group("end")) and end.month < start.month:
                end = end.replace(year=start.year + 1)
            dates.update(_expand_announcement_date_range(start, end))
        except ValueError:
            continue

    single_date_clause = ANNOUNCEMENT_RANGE_PATTERN.sub(" ", clause)
    for match in ANNOUNCEMENT_DATE_PATTERN.finditer(single_date_clause):
        try:
            dates.add(_parse_announcement_date_token(match.group(0), default_year))
        except ValueError:
            continue
    return dates


def _parse_announcement_date_token(token: str, default_year: int) -> date:
    text = re.sub(r"\s+", "", token)
    full_match = re.search(r"(20\d{2})\D*(\d{1,2})\D*(\d{1,2})", text)
    if full_match:
        return date(int(full_match.group(1)), int(full_match.group(2)), int(full_match.group(3)))
    month_day_match = re.search(r"(\d{1,2})\D+(\d{1,2})", text)
    if not month_day_match:
        raise ValueError(f"无法识别公告日期：{token}")
    return date(default_year, int(month_day_match.group(1)), int(month_day_match.group(2)))


def _announcement_token_has_year(token: str) -> bool:
    return re.search(r"20\d{2}", token) is not None


def _expand_announcement_date_range(start: date, end: date) -> set[date]:
    if end < start or (end - start).days > 370:
        return set()
    return {start + timedelta(days=offset) for offset in range((end - start).days + 1)}


def _is_announcement_holiday_clause(clause: str) -> bool:
    return any(keyword in clause for keyword in HOLIDAY_KEYWORDS)


def _is_announcement_trading_clause(clause: str) -> bool:
    if any(keyword in clause for keyword in HOLIDAY_KEYWORDS):
        return False
    return any(keyword in clause for keyword in TRADING_KEYWORDS)


def _trade_dates_from_source(source: str, params: dict[str, Any]) -> list[date]:
    if source == INLINE_SOURCE:
        return _inline_trade_dates(params)
    if source == AKSHARE_SINA_SOURCE:
        return _akshare_sina_trade_dates()
    raise ValueError(f"不支持的交易日历数据源：{source}")


def _akshare_sina_trade_dates() -> list[date]:
    akshare = importlib.import_module("akshare")
    frame = akshare.tool_trade_date_hist_sina()
    if "trade_date" not in frame:
        raise ValueError("AKShare 交易日历结果缺少 trade_date 列。")
    return sorted({_parse_date(value) for value in frame["trade_date"].tolist()})


def _inline_trade_dates(params: dict[str, Any]) -> list[date]:
    raw = params.get("trade_dates") or params.get("trading_days") or params.get("dates") or []
    if isinstance(raw, str):
        items = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, list | tuple | set):
        items = list(raw)
    else:
        items = [raw]
    dates = {_parse_date(item) for item in items if str(item).strip()}
    return sorted(dates)


def _compact_calendar_dates(range_start: date, range_end: date, trade_dates: set[date]) -> tuple[list[str], list[str]]:
    holidays: list[str] = []
    weekend_trading_days: list[str] = []
    current = range_start
    while current <= range_end:
        if current.weekday() < 5 and current not in trade_dates:
            holidays.append(current.isoformat())
        if current.weekday() >= 5 and current in trade_dates:
            weekend_trading_days.append(current.isoformat())
        current += timedelta(days=1)
    return holidays, weekend_trading_days


def _calendar_write_path(params: dict[str, Any]) -> Path:
    settings = get_settings()
    raw = params.get("calendar_path") or params.get("trading_calendar_path") or settings.trading_calendar_path
    path = Path(str(raw)) if raw else Path("egs/trading_calendar.yaml")
    resolved = path if path.is_absolute() else (settings.project_root / path)
    resolved = resolved.resolve()
    _ensure_project_path(resolved)
    return resolved


def _official_calendar_write_path(params: dict[str, Any]) -> Path:
    path = _reference_calendar_path(params) or (get_settings().project_root / "egs" / "trading_calendar.official.yaml")
    resolved = path.resolve()
    _ensure_project_path(resolved)
    return resolved


def _calendar_status_path(params: dict[str, Any]) -> Path:
    settings = get_settings()
    raw = params.get("calendar_path") or params.get("trading_calendar_path") or settings.trading_calendar_path
    path = Path(str(raw)) if raw else Path("egs/trading_calendar.yaml")
    return (path if path.is_absolute() else (settings.project_root / path)).resolve()


def _reference_calendar_path(params: dict[str, Any]) -> Path | None:
    raw = (
        params.get("official_calendar_path")
        or params.get("reference_calendar_path")
        or params.get("calendar_reference_path")
        or params.get("exchange_calendar_path")
    )
    if raw in (None, ""):
        return None
    path = Path(str(raw))
    return (path if path.is_absolute() else (get_settings().project_root / path)).resolve()


def _load_calendar_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"file_format": "yaml", "markets": {}}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {"file_format": "yaml", "markets": {}}


def _calendar_for_market(payload: dict[str, Any], market: str) -> dict[str, Any] | None:
    markets = payload.get("markets", {})
    calendar = markets.get(market) if isinstance(markets, dict) else None
    return calendar if isinstance(calendar, dict) else None


def _diff_window(
    params: dict[str, Any],
    current_calendar: dict[str, Any],
    reference_calendar: dict[str, Any],
) -> tuple[date, date] | None:
    explicit_start = _date_param(params, "diff_range_start") or _date_param(params, "range_start")
    explicit_end = _date_param(params, "diff_range_end") or _date_param(params, "range_end")
    current_start = _optional_date(current_calendar.get("range_start"))
    current_end = _optional_date(current_calendar.get("range_end"))
    reference_start = _optional_date(reference_calendar.get("range_start"))
    reference_end = _optional_date(reference_calendar.get("range_end"))
    starts = [item for item in (explicit_start, current_start, reference_start) if item is not None]
    ends = [item for item in (explicit_end, current_end, reference_end) if item is not None]
    if not starts or not ends:
        return None
    start = max(starts)
    end = min(ends)
    if start > end:
        return None
    return start, end


def _calendar_trade_dates(calendar: dict[str, Any], start: date, end: date) -> set[date]:
    trading_days = {_parse_date(item) for item in _list_value(calendar.get("trading_days"))}
    compact = _calendar_is_compact(calendar)
    if trading_days and not compact:
        return {item for item in trading_days if start <= item <= end}
    holidays = {_parse_date(item) for item in _list_value(calendar.get("holidays"))}
    trade_dates: set[date] = set()
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            trade_dates.add(current)
        current += timedelta(days=1)
    return trade_dates | {item for item in trading_days if start <= item <= end}


def _calendar_is_compact(calendar: dict[str, Any]) -> bool:
    metadata = calendar.get("metadata")
    if isinstance(metadata, dict) and "compact" in metadata:
        return _bool_param(metadata, "compact", True)
    return True


def _ensure_project_path(path: Path) -> None:
    project_root = get_settings().project_root.resolve()
    try:
        path.resolve().relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"交易日历自动更新只能访问项目目录内路径：{path}") from exc


def _market_from_params(params: dict[str, Any]) -> str:
    return str(params.get("calendar_market") or params.get("market") or DEFAULT_MARKET).strip() or DEFAULT_MARKET


def _source_from_params(params: dict[str, Any]) -> str:
    source = str(params.get("calendar_source") or params.get("source") or AKSHARE_SINA_SOURCE).strip().lower()
    return source.replace("-", "_")


def _date_param(params: dict[str, Any], key: str) -> date | None:
    value = params.get(key)
    if value in (None, ""):
        return None
    return _parse_date(value)


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return datetime.fromisoformat(text).date()


def _optional_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    try:
        return _parse_date(value)
    except (TypeError, ValueError):
        return None


def _optional_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _bool_param(params: dict[str, Any], key: str, default: bool) -> bool:
    value = params.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "启用", "是"}
    return bool(value)


def _int_param(params: dict[str, Any], key: str, default: int) -> int:
    value = params.get(key, default)
    if value in (None, ""):
        return default
    return int(value)


def _list_value(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [value]
