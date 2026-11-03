"""Frontend-only option lists and default payloads."""

JOB_TYPE_OPTIONS = [
    "news_fetch",
    "market_refresh",
    "backtest",
    "paper_check",
    "recommend",
    "report",
    "calendar_refresh",
    "calendar_reference_refresh",
    "calendar_announcement_profile_check",
    "system_health_check",
    "data_maintain",
    "kb_sync",
    "custom",
]

DEFAULT_JOB_PARAMS = """{
  "trading_day_only": false,
  "calendar_path": "",
  "official_calendar_path": "",
  "announcement_profiles_path": "egs/exchange_announcement_profiles.yaml",
  "announcement_profile": "",
  "announcement_profile_min_links": 1,
  "announcement_profile_check_limit": 5,
  "retry_times": 0,
  "retry_interval_seconds": 0,
  "timeout_seconds": 0,
  "timeout_mode": "thread",
  "mutex_group": "",
  "calendar_warn_days": 14,
  "calendar_stale_days": 14,
  "calendar_diff_limit": 20
}"""
