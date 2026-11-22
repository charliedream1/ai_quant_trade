"""Deterministic evidence, keyword mode and stock readout regression checks."""

from src.core.page_analysis_snapshot import _economic_evidence
from src.engine.market import news_bge
from src.frontend.service.home_views import theme_summary
from src.frontend.service.stock_indicators import indicator_rows


def test_local_keyword_mode_never_invokes_semantic_backend(monkeypatch):
    items = [{"title": "先进封装设备订单", "source": "Source"}]
    calls = []

    def extract(rows, *, lexical_label):
        calls.append(lexical_label)
        return rows, "Local BERT test"

    monkeypatch.setattr(news_bge, "extract_phrases", extract)
    assert "TF-IDF" in theme_summary(items)
    assert calls == []
    assert "Local BERT test" in theme_summary(items, "semantic")
    assert len(calls) == 1


def test_semantic_extraction_keeps_only_evidenced_phrases(monkeypatch):
    rows = [
        {"keyword": "First phrase", "headline": "An original headline"},
        {"keyword": "Second phrase", "headline": "An original headline"},
    ]
    monkeypatch.setattr(news_bge, "_provider", lambda: ("local", lambda texts: [[0, 1], [1, 0], [1, 0]]))
    result, label = news_bge.extract_phrases(rows, lexical_label="TF-IDF")
    assert label == "本地 BGE 语义抽取"
    assert result == [rows[1], rows[0]]


def test_macro_report_preserves_latest_rows_for_each_series():
    observations = [
        {"series": series, "observation_date": f"2026-01-{day:02d}", "value": day}
        for series in ("cpi", "pmi")
        for day in range(1, 12)
    ]
    snapshot = {
        "kind": "macro",
        "snapshot_id": "accepted",
        "observations": observations,
        "sources": {"cpi": {"timestamp": "2026-01-12"}},
    }
    result = _economic_evidence(("status", None, "unused chart", snapshot), 3)
    assert result["snapshot_id"] == "accepted" and result["sources"] == snapshot["sources"]
    assert [row["value"] for row in result["recent_observations_by_series"]["pmi"]] == [9, 10, 11]


def test_indicators_explain_trend_and_match_benchmark_dates():
    bars = [{"date": f"D-{day:03d}", "close": 100 + day, "volume": 500} for day in range(70)]
    benchmark = [{**row, "close": 100} for row in bars]
    rows = {row["指标"]: row for row in indicator_rows(bars, benchmark)}
    assert rows["RSI14"]["数值"] == 100
    assert "偏强" in rows["MA20"]["解读"]
    assert rows["60 根 K 线相对上证综合（百分点）"]["数值"] > 0
    assert all(row["数值"] is None for row in indicator_rows(bars[:2]))
