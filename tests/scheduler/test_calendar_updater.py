from datetime import date
from pathlib import Path

import yaml

from src.scheduler.calendar_updater import (
    refresh_official_trading_calendar,
    refresh_trading_calendar,
    trading_calendar_alerts,
    trading_calendar_diff,
    trading_calendar_status,
    validate_announcement_profiles,
)
from src.scheduler.jobs import execute_scheduled_job
from src.scheduler.policies import is_trading_day


def test_refresh_trading_calendar_writes_compact_yaml():
    calendar_path = _project_tmp_calendar("compact-calendar.yaml")
    result = refresh_trading_calendar(
        {
            "source": "inline",
            "market": "cn_stock",
            "calendar_path": str(calendar_path),
            "trade_dates": ["2026-09-28", "2026-09-29", "2026-10-03"],
            "range_start": "2026-09-28",
            "range_end": "2026-10-04",
        }
    )
    payload = yaml.safe_load(calendar_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.trading_day_count == 3
    assert calendar["holidays"] == ["2026-09-30", "2026-10-01", "2026-10-02"]
    assert calendar["trading_days"] == ["2026-10-03"]
    assert not is_trading_day(date(2026, 9, 30), calendar)
    assert is_trading_day(date(2026, 10, 3), calendar)


def test_calendar_refresh_scheduled_job_returns_summary():
    calendar_path = _project_tmp_calendar("job-calendar.yaml")
    result = execute_scheduled_job(
        {
            "job_type": "calendar_refresh",
            "target": {
                "source": "inline",
                "calendar_path": str(calendar_path),
                "trade_dates": "2026-09-28,2026-09-29",
                "range_start": "2026-09-28",
                "range_end": "2026-09-30",
            },
        }
    )

    assert result["status"] == "成功"
    assert "交易日历更新完成" in result["summary"]
    assert result["details"]["holiday_count"] == 1


def test_calendar_reference_refresh_scheduled_job_returns_summary():
    reference_path = _project_tmp_calendar("job-official-reference.yaml")
    result = execute_scheduled_job(
        {
            "job_type": "calendar_reference_refresh",
            "target": {
                "official_calendar_path": str(reference_path),
                "range_start": "2026-09-28",
                "range_end": "2026-10-04",
                "holidays": ["2026-10-01"],
                "trading_days": ["2026-10-03"],
            },
        }
    )

    assert result["status"] == "成功"
    assert "官方参考日历更新完成" in result["summary"]
    assert result["details"]["holiday_count"] == 1


def test_calendar_announcement_profile_check_scheduled_job_returns_summary(monkeypatch):
    profile_path = _project_tmp_calendar("job-exchange-announcement-profiles.yaml")
    index_url = "https://example.com/profile-check/"
    notice_url = "https://example.com/profile-check/holiday.html"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "file_format": "yaml",
                "profiles": {
                    "cn_stock_test": {
                        "announcement_index_url": index_url,
                        "announcement_link_keywords": ["休市安排"],
                        "announcement_discovery_limit": 1,
                    }
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    payloads = {index_url: '<a href="holiday.html">端午节休市安排</a>'.encode()}

    def fake_urlopen(request, timeout):
        return _FakeUrlResponse(payloads[request.full_url])

    monkeypatch.setattr("src.scheduler.calendar_updater.urlopen", fake_urlopen)
    direct_result = validate_announcement_profiles(
        {
            "announcement_profiles_path": str(profile_path),
            "announcement_profile": "cn_stock_test",
            "announcement_profile_min_links": 1,
        }
    )
    result = execute_scheduled_job(
        {
            "job_type": "calendar_announcement_profile_check",
            "target": {
                "announcement_profiles_path": str(profile_path),
                "announcement_profile": "cn_stock_test",
                "announcement_profile_min_links": 1,
            },
        }
    )

    assert direct_result["status"] == "ok"
    assert result["status"] == "成功"
    assert "交易所公告源核验完成" in result["summary"]
    assert result["details"]["status"] == "ok"
    assert result["details"]["profiles"][0]["sample_candidate_urls"] == [notice_url]


def test_trading_calendar_status_reports_counts_and_missing_file():
    missing_path = _project_tmp_calendar("missing-calendar.yaml")
    status = trading_calendar_status({"calendar_path": str(missing_path)})
    assert status["status"] == "missing"

    calendar_path = _project_tmp_calendar("status-calendar.yaml")
    refresh_trading_calendar(
        {
            "source": "inline",
            "calendar_path": str(calendar_path),
            "trade_dates": ["2026-09-28", "2026-10-03"],
            "range_start": "2026-09-28",
            "range_end": "2026-10-03",
        }
    )
    status = trading_calendar_status({"calendar_path": str(calendar_path)})

    assert status["status"] == "ok"
    assert status["holiday_count"] == 4
    assert status["trading_day_count"] == 1
    assert status["metadata"]["trading_day_count"] == 2


def test_trading_calendar_alerts_report_missing_and_expiring_calendar():
    missing_path = _project_tmp_calendar("alert-missing-calendar.yaml")
    missing_alerts = trading_calendar_alerts({"calendar_path": str(missing_path)})
    assert missing_alerts[0]["severity"] == "critical"
    assert missing_alerts[0]["code"] == "calendar_missing"

    calendar_path = _project_tmp_calendar("alert-expiring-calendar.yaml")
    refresh_trading_calendar(
        {
            "source": "inline",
            "calendar_path": str(calendar_path),
            "trade_dates": ["2026-09-28", "2026-09-29", "2026-10-03"],
            "range_start": "2026-09-28",
            "range_end": "2026-10-03",
        }
    )
    alerts = trading_calendar_alerts(
        {
            "calendar_path": str(calendar_path),
            "as_of_date": "2026-10-02",
            "calendar_warn_days": 3,
            "calendar_stale_days": 0,
        }
    )
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["code"] == "calendar_expiring"
    assert alerts[0]["days_left"] == 1


def test_trading_calendar_diff_checks_official_reference_calendar():
    calendar_path = _project_tmp_calendar("diff-current-calendar.yaml")
    reference_path = _project_tmp_calendar("diff-official-calendar.yaml")
    refresh_trading_calendar(
        {
            "source": "inline",
            "calendar_path": str(calendar_path),
            "trade_dates": ["2026-09-28", "2026-09-29"],
            "range_start": "2026-09-28",
            "range_end": "2026-10-04",
        }
    )
    refresh_trading_calendar(
        {
            "source": "inline",
            "calendar_path": str(reference_path),
            "trade_dates": ["2026-09-28", "2026-09-29", "2026-10-03"],
            "range_start": "2026-09-28",
            "range_end": "2026-10-04",
        }
    )

    params = {
        "calendar_path": str(calendar_path),
        "official_calendar_path": str(reference_path),
        "as_of_date": "2026-09-28",
        "calendar_warn_days": 0,
        "calendar_stale_days": 0,
    }
    diff = trading_calendar_diff(params)
    assert diff["status"] == "mismatch"
    assert diff["missing_trading_day_count"] == 1
    assert diff["extra_trading_day_count"] == 0
    assert diff["missing_trading_days"] == ["2026-10-03"]

    alerts = trading_calendar_alerts(params)
    diff_alert = next(item for item in alerts if item["code"] == "calendar_official_diff")
    assert diff_alert["severity"] == "critical"
    assert diff_alert["diff"]["missing_trading_days"] == ["2026-10-03"]


def test_refresh_official_trading_calendar_writes_reference_yaml():
    reference_path = _project_tmp_calendar("official-reference.yaml")
    result = refresh_official_trading_calendar(
        {
            "official_calendar_path": str(reference_path),
            "range_start": "2026-09-28",
            "range_end": "2026-10-04",
            "holidays": ["2026-10-01", "2026-10-02"],
            "trading_days": ["2026-10-03"],
            "official_source": "official-announcement-manual",
        }
    )
    payload = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.holiday_count == 2
    assert result.weekend_trading_day_count == 1
    assert calendar["source"] == "official-announcement-manual"
    assert calendar["metadata"]["official_reference"] is True
    assert calendar["holidays"] == ["2026-10-01", "2026-10-02"]
    assert calendar["trading_days"] == ["2026-10-03"]


def test_refresh_official_trading_calendar_parses_announcement_text():
    reference_path = _project_tmp_calendar("official-reference-from-text.yaml")
    result = refresh_official_trading_calendar(
        {
            "official_calendar_path": str(reference_path),
            "range_start": "2026-09-28",
            "range_end": "2026-10-04",
            "announcement_text": (
                "根据交易所公告，2026年10月1日（星期四）至10月2日（星期五）休市，"
                "10月3日（星期六）照常开市。10月4日（星期日）为周末休市。"
            ),
        }
    )
    payload = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.parsed_from_announcement is True
    assert result.announcement_date_count == 3
    assert result.holiday_count == 2
    assert result.weekend_trading_day_count == 1
    assert calendar["source"] == "official-announcement-parser"
    assert calendar["metadata"]["parsed_from_announcement"] is True
    assert calendar["holidays"] == ["2026-10-01", "2026-10-02"]
    assert calendar["trading_days"] == ["2026-10-03"]


def test_refresh_official_trading_calendar_reads_project_announcement_file():
    reference_path = _project_tmp_calendar("official-reference-from-file.yaml")
    announcement_path = _project_tmp_calendar("official-announcement.txt")
    announcement_path.write_text("2026年4月6日休市，4月4日照常开市。", encoding="utf-8")
    result = refresh_official_trading_calendar(
        {
            "official_calendar_path": str(reference_path),
            "range_start": "2026-04-01",
            "range_end": "2026-04-06",
            "announcement_path": str(announcement_path),
        }
    )
    payload = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.parsed_from_announcement is True
    assert calendar["holidays"] == ["2026-04-06"]
    assert calendar["trading_days"] == ["2026-04-04"]


def test_refresh_official_trading_calendar_reads_announcement_url(monkeypatch):
    reference_path = _project_tmp_calendar("official-reference-from-url.yaml")
    announcement_url = "https://example.com/calendar-notice.html"

    def fake_urlopen(request, timeout):
        assert request.full_url == announcement_url
        assert timeout == 3
        return _FakeUrlResponse(
            ("<html><body><p>交易所公告：2026年5月1日至5月3日休市。</p><p>5月9日照常开市。</p></body></html>").encode()
        )

    monkeypatch.setattr("src.scheduler.calendar_updater.urlopen", fake_urlopen)
    result = refresh_official_trading_calendar(
        {
            "official_calendar_path": str(reference_path),
            "range_start": "2026-05-01",
            "range_end": "2026-05-10",
            "announcement_url": announcement_url,
            "announcement_url_timeout_seconds": 3,
        }
    )
    payload = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.parsed_from_announcement is True
    assert calendar["source"] == "official-announcement-url"
    assert calendar["metadata"]["announcement_urls"] == [announcement_url]
    assert calendar["holidays"] == ["2026-05-01"]
    assert calendar["trading_days"] == ["2026-05-09"]


def test_refresh_official_trading_calendar_discovers_announcement_from_index(monkeypatch):
    reference_path = _project_tmp_calendar("official-reference-from-index.yaml")
    index_url = "https://example.com/notices/"
    notice_url = "https://example.com/notices/calendar-2026.html"
    payloads = {
        index_url: (
            "<html><body>"
            '<a href="other.html">上市公告</a>'
            '<a href="./calendar-2026.html">2026年节假日休市安排公告</a>'
            "</body></html>"
        ).encode(),
        notice_url: ("<html><body><p>2026年6月18日至6月19日休市。</p><p>6月20日照常开市。</p></body></html>").encode(),
    }

    def fake_urlopen(request, timeout):
        assert timeout == 4
        return _FakeUrlResponse(payloads[request.full_url])

    monkeypatch.setattr("src.scheduler.calendar_updater.urlopen", fake_urlopen)
    result = refresh_official_trading_calendar(
        {
            "official_calendar_path": str(reference_path),
            "range_start": "2026-06-15",
            "range_end": "2026-06-21",
            "announcement_index_url": index_url,
            "announcement_url_timeout_seconds": 4,
        }
    )
    payload = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.parsed_from_announcement is True
    assert calendar["source"] == "official-announcement-discovery"
    assert calendar["metadata"]["announcement_index_urls"] == [index_url]
    assert calendar["metadata"]["announcement_urls"] == [notice_url]
    assert calendar["holidays"] == ["2026-06-18", "2026-06-19"]
    assert calendar["trading_days"] == ["2026-06-20"]


def test_refresh_official_trading_calendar_uses_announcement_profile(monkeypatch):
    reference_path = _project_tmp_calendar("official-reference-from-profile.yaml")
    profile_path = _project_tmp_calendar("exchange-announcement-profiles.yaml")
    index_url = "https://example.com/profile-notices/"
    notice_url = "https://example.com/profile-notices/holiday.html"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "file_format": "yaml",
                "profiles": {
                    "cn_stock_test": {
                        "announcement_index_url": index_url,
                        "announcement_link_keywords": ["休市安排"],
                        "announcement_discovery_limit": 1,
                    }
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    payloads = {
        index_url: '<a href="holiday.html">端午节休市安排</a>'.encode(),
        notice_url: "2026年9月21日休市，9月19日照常开市。".encode(),
    }

    def fake_urlopen(request, timeout):
        return _FakeUrlResponse(payloads[request.full_url])

    monkeypatch.setattr("src.scheduler.calendar_updater.urlopen", fake_urlopen)
    result = refresh_official_trading_calendar(
        {
            "official_calendar_path": str(reference_path),
            "range_start": "2026-09-18",
            "range_end": "2026-09-21",
            "announcement_profile": "cn_stock_test",
            "announcement_profiles_path": str(profile_path),
        }
    )
    payload = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    calendar = payload["markets"]["cn_stock"]

    assert result.parsed_from_announcement is True
    assert calendar["source"] == "official-announcement-discovery"
    assert calendar["metadata"]["announcement_index_urls"] == [index_url]
    assert calendar["metadata"]["announcement_urls"] == [notice_url]
    assert calendar["holidays"] == ["2026-09-21"]
    assert calendar["trading_days"] == ["2026-09-19"]


class _FakeHeaders:
    def get_content_charset(self):
        return "utf-8"


class _FakeUrlResponse:
    headers = _FakeHeaders()

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size: int) -> bytes:
        return self.payload[:size]


def _project_tmp_calendar(name: str) -> Path:
    path = Path.cwd() / ".pytest_tmp" / "scheduler_calendar" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return path
