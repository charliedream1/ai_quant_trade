"""Partial history cannot break valid reports or create a new generation job."""

from uuid import uuid4

from src.engine.insights.service import InsightReportService
from src.engine.insights.store import InsightStore
from src.engine.market.report_generator import MarketReportGenerator
from src.frontend.services import FrontendService


def seed(store, status, title, created):
    key = uuid4().hex
    store.save(
        {"run_id": key, "status": status, "request": {"kind": "market_review"}, "title": title, "created_at": created}
    )
    return f"skill:{key}"


def test_filters_selection_invalid_record_and_missing_html(client, monkeypatch):
    monkeypatch.setattr(
        InsightReportService, "start", lambda *args: (_ for _ in ()).throw(AssertionError("no generation"))
    )
    service, store = FrontendService(), InsightStore()
    first = seed(store, "partial", "中文市场复盘", "2026-10-26T10:00:00+08:00")
    later = seed(store, "failed", "Other report", "2026-10-26T03:00:00Z")
    broken = store.directory(uuid4().hex)
    broken.mkdir()
    (broken / "run.json").write_text("{}", encoding="utf-8")
    MarketReportGenerator().create({"topic": "Template fixture", "use_llm": False})
    frame, update = service.report_library_list(first)
    assert first in set(frame["key"]) and later in set(frame["key"])
    assert list(frame[frame["来源"] == "Skill报告"]["key"]) == [later, first]
    assert update["value"] == first
    frame, update = service.report_library_list(first, "skill", "partial", "市场")
    assert list(frame["key"]) == [first] and update["value"] == first
    frame, update = service.report_library_list(first, "model", "all", "")
    assert len(frame) == 1 and update["value"] is None
    status, process, html, download = service.report_library_open(first)
    assert "文件缺失" in status and "缺口" in status and "未找到过程文件" in process
    assert "不可预览或下载" in html and download is None
    failed, process, _, download = service.report_library_open(later)
    assert "失败" in failed and download is None


def test_corrupt_events_skip_only_invalid_lines(client):
    store = InsightStore()
    key = seed(store, "partial", "Event fixture", "2026-10-26T03:00:00Z").split(":")[1]
    store.append(key, "actual", "Preserved real event")
    with (store.directory(key) / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{bad\n{}\n")
    assert len(store.events(key)) == 1
    _, process, _, _ = FrontendService().report_library_open("skill:" + key)
    assert "Preserved real event" in process
