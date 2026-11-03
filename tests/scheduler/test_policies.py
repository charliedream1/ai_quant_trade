from datetime import UTC, date, datetime

from src.scheduler.policies import (
    is_trading_day,
    mutex_group_from_params,
    retry_policy_from_params,
    timeout_mode_from_params,
    timeout_seconds_from_params,
    trading_day_skip_summary,
)


def test_trading_day_policy_supports_weekends_and_overrides():
    assert not is_trading_day(date(2026, 10, 3))
    assert is_trading_day(date(2026, 10, 3), {"extra_trading_days": ["2026-10-03"]})
    assert not is_trading_day(date(2026, 9, 30), {"holidays": ["2026-09-30"]})

    summary = trading_day_skip_summary(
        {"trading_day_only": True, "trading_calendar": {"holidays": ["2026-09-30"]}},
        now=datetime(2026, 9, 30, 1, 0, tzinfo=UTC),
    )
    assert summary is not None
    assert "2026-09-30" in summary


def test_trading_day_policy_loads_calendar_file(tmp_path):
    calendar_path = tmp_path / "trading_calendar.yaml"
    calendar_path.write_text(
        "\n".join(
            [
                "markets:",
                "  cn_stock:",
                "    holidays:",
                "      - 2026-09-30",
                "    trading_days:",
                "      - 2026-10-03",
                "",
            ]
        ),
        encoding="utf-8",
    )

    holiday_summary = trading_day_skip_summary(
        {"trading_day_only": True, "calendar_path": str(calendar_path)},
        now=datetime(2026, 9, 30, 1, 0, tzinfo=UTC),
    )
    make_up_summary = trading_day_skip_summary(
        {"trading_day_only": True, "calendar_path": str(calendar_path)},
        now=datetime(2026, 10, 3, 1, 0, tzinfo=UTC),
    )
    inline_override_summary = trading_day_skip_summary(
        {
            "trading_day_only": True,
            "calendar_path": str(calendar_path),
            "trading_calendar": {"extra_trading_days": ["2026-09-30"]},
        },
        now=datetime(2026, 9, 30, 1, 0, tzinfo=UTC),
    )

    assert holiday_summary is not None
    assert make_up_summary is None
    assert inline_override_summary is None


def test_retry_policy_uses_bounded_attempts_and_backoff():
    policy = retry_policy_from_params({"retry_times": 2, "retry_interval_seconds": 3, "retry_backoff": 3})

    assert policy.max_attempts == 3
    assert policy.delay_seconds(1) == 0
    assert policy.delay_seconds(2) == 3
    assert policy.delay_seconds(3) == 9
    assert timeout_seconds_from_params({"timeout_minutes": 2}) == 120
    assert mutex_group_from_params({"mutex_group": " research "}) == "research"
    assert mutex_group_from_params({"mutex": "qlib"}) == "qlib"
    assert mutex_group_from_params({"mutex_group": ""}) is None
    assert timeout_mode_from_params({}) == "process"
    assert timeout_mode_from_params({"timeout_mode": "thread"}) == "thread"
    assert timeout_mode_from_params({"timeout_mode": "process"}) == "process"
    assert timeout_mode_from_params({"hard_timeout": True}) == "process"
