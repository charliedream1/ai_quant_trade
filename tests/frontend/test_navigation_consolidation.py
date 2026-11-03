"""Old links resolve to canonical workspaces; report origins and content stay distinct."""

from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from src.engine.insights.store import InsightStore
from src.engine.market.report_generator import MarketReportGenerator
from src.frontend.common.navigation import resolve_destination, workspace_link
from src.frontend.registry import MODULES
from src.frontend.services import FrontendService


@pytest.mark.parametrize("view,tab", [("reports", "研报检索"), ("papers", "论文检索"), ("", "研报检索")])
def test_legacy_research_roots_preserve_selected_content(client, view, tab):
    response = client.get(f"/app/research/?view={view}", follow_redirects=False)
    assert response.status_code == 307
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query == {"module": ["knowledge"], "view": ["research"], "tab": [tab]}


def test_canonical_navigation_and_single_rag_interface(client):
    assert len(MODULES) == 9 and "research" not in {module.key for module in MODULES}
    strategy = next(module for module in MODULES if module.key == "strategy")
    assert strategy.views[0] == ("workshop", "图形策略工坊")
    assert ("etf", "ETF研究") in strategy.views
    assert resolve_destination("market", "factors") == {"module": "strategy", "view": "factors", "tab": ""}
    config = client.get("/app/knowledge/config").json()
    labels = [item["props"].get("label") for item in config["components"]]
    assert labels.count("会话 ID") == 1 and "本次不带历史" not in labels
    assert "rag-chat-history" in [item["props"].get("elem_id") for item in config["components"]]


def test_report_catalog_keeps_origin_and_escaped_legacy_content(client):
    service = FrontendService()
    model = MarketReportGenerator().create({"topic": "<script>bad()</script>", "use_llm": False})
    store, key = InsightStore(), uuid4().hex
    store.save(
        {
            "run_id": key,
            "status": "partial",
            "request": {"kind": "market_review"},
            "created_at": "2026-10-26T00:00:00Z",
            "title": "Fixture evidence report",
        }
    )
    store.append(key, "fixture", "Explicit test evidence, no model invoked")
    (store.directory(key) / "report.html").write_text("<!doctype html><p>Fixture report</p>", encoding="utf-8")
    frame, choices = service.report_library_list()
    assert set(frame["来源"]) == {"旧版模板报告", "Skill报告"}
    assert len(choices["choices"]) == 2
    status, process, preview, download = service.report_library_open(f"skill:{key}")
    assert "缺口" in status
    assert "fixture" in process and 'sandbox="allow-scripts"' in preview and download.endswith("report.html")
    status, _, preview, download = service.report_library_open(f"model:{model['report_id']}")
    assert "旧版模板" in status and "<script>bad()" not in preview and "&lt;script&gt;" in preview
    assert download is None
    with pytest.raises(ValueError):
        service.report_library_open("../../wrong")


def test_context_link_escapes_html_and_preserves_task_identity():
    html = workspace_link("<打开结果>", "simulation", "backtest", task_id=17, strategy_id=2)
    assert "task_id=17" in html and "strategy_id=2" in html and "&lt;打开结果&gt;" in html
