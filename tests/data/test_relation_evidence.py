"""News provenance and return interval correctness."""

import pytest
from gradio.components.plot import PlotData

from src.data.relation_evidence import dated_returns, news_evidence, return_correlation
from src.frontend.service.relation_layout import bounds, evidence_html, plot_metadata, positions
from src.frontend.service.visuals import relation_figure


def test_actual_gradio_plot_input_retains_evidence():
    value = PlotData(type="plotly", plot='{"layout":{"meta":{"relation_edges":[{"source":"A","target":"B"}]}}}')
    assert plot_metadata(value)["relation_edges"][0]["source"] == "A"


def test_query_injected_keywords_are_not_entity_evidence():
    article = {"title": "半导体行业景气提升", "summary": "芯片市场观察", "keywords": ["600519"], "symbols": ["600519"]}
    assert news_evidence(article, "600519", "贵州茅台") is None
    article["summary"] = "贵州茅台发布经营公告"
    evidence = news_evidence(article, "600519", "贵州茅台")
    assert evidence["matched_field"] == "summary"
    assert evidence["matched_entity"] in evidence["excerpt"]
    article = {"title": "公司公告", "source_symbols": ["600519"]}
    assert news_evidence(article, "600519", "贵州茅台")["method"] == "provider_security_tag"


def test_evidence_html_escapes_text_and_rejects_non_http_urls():
    html = evidence_html(
        {"relation_type": "news", "evidence": {"title": "<script>alert(1)</script>", "url": "javascript:alert(1)"}}
    )
    assert "<script>" not in html and "javascript:" not in html
    assert "&lt;script&gt;" in html


def test_returns_use_identical_intervals_and_preserve_negative_sign():
    rows = [{"date": f"2025-01-{index:02d}", "close": 100 + index**2} for index in range(1, 29)]
    left = dated_returns(rows)
    right = {key: -value for key, value in left.items()}
    coefficient, metadata = return_correlation(left, right)
    assert coefficient == pytest.approx(-1)
    assert metadata["sample_size"] == 27
    missing = dated_returns(rows[:10] + rows[11:])
    assert "2025-01-10/2025-01-12" in missing
    assert "2025-01-10/2025-01-12" not in left
    _, metadata = return_correlation(left, missing)
    assert metadata["sample_size"] == 25


def test_sparse_graph_uses_available_viewport():
    nodes = [{"id": key} for key in "ABCD"]
    edges = [{"source": a, "target": b} for a, b in zip("ABC", "BCD", strict=True)]
    coordinates = positions(nodes, edges, "A")
    x, y = bounds(coordinates)
    assert min(value[0] for value in coordinates.values()) < 0
    assert max(value[0] for value in coordinates.values()) > 0
    assert all(x[0] <= value[0] <= x[1] and y[0] <= value[1] <= y[1] for value in coordinates.values())
    figure = relation_figure(nodes, edges, "A")
    assert figure.layout.legend.xanchor == "left"
    assert figure.layout.legend.x == 0
