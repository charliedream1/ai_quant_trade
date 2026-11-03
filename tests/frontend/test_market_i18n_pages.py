import json

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.data import (
    MARKET_CN,
    MARKET_US,
    DataSourceManager,
    current_market,
    normalize_market,
    set_current_market,
)
from src.data.manager import MockDataSource
from src.frontend.services import (
    _DAILY_UI_CACHE,
    FrontendService,
    model_stat_figure,
    paper_distribution_figure,
    report_rating_figure,
    strategy_stat_figure,
    styled_frame,
    switch_ui_market,
)


@pytest.fixture(autouse=True)
def _isolate_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "market_test.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "mock")
    import src.core.config as config_module
    from src.core.database import Database

    config_module._SETTINGS = None
    Database.reset_instance()
    original = current_market()
    _DAILY_UI_CACHE.clear()
    yield
    set_current_market(original)
    _DAILY_UI_CACHE.clear()
    Database.reset_instance()
    config_module._SETTINGS = None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A股", MARKET_CN),
        ("cn", MARKET_CN),
        ("US", MARKET_US),
        ("美股", MARKET_US),
        ("usa", MARKET_US),
        (None, MARKET_CN),
        ("", MARKET_CN),
    ],
)
def test_normalize_market_labels(raw, expected):
    assert normalize_market(raw) == expected


def test_market_state_round_trip():
    assert set_current_market("美股") == MARKET_US
    assert current_market() == MARKET_US
    assert set_current_market("A股") == MARKET_CN
    assert current_market() == MARKET_CN


def test_mock_source_us_datasets():
    source = MockDataSource(market=MARKET_US)
    indices = source.indices()
    assert indices and indices[0]["name"] == "S&P 500"
    quote = source.stock_quote("NVDA")
    assert quote["name"] == "NVIDIA Corp."
    news = source.list_news(category="company")
    assert news and all("NVDA" in " ".join(item["symbols"]) or item["symbols"] == [] for item in news)
    reports = source.reports()
    assert reports and reports[0]["org"] == "Mock Research"


def test_mock_source_cn_unchanged_after_us_switch():
    set_current_market(MARKET_US)
    us_source = MockDataSource()
    assert us_source.indices()[0]["name"] == "S&P 500"
    set_current_market(MARKET_CN)
    cn_source = MockDataSource()
    assert cn_source.indices()[0]["name"] == "上证指数"


def test_mock_news_list_is_scoped_to_current_market():
    from src.engine.market import NewsAggregator

    set_current_market(MARKET_US)
    us_news = NewsAggregator().list_news(None, None, None, 1, 10, refresh=True)["items"]
    assert us_news and all(item["source"] == "Mock Wire" for item in us_news)
    assert any("S&P 500" in item["keywords"] or "NVIDIA" in item["title"] for item in us_news)

    set_current_market(MARKET_CN)
    cn_news = NewsAggregator().list_news(None, None, None, 1, 10, refresh=True)["items"]
    assert cn_news and all(item["source"] == "本地模拟源" for item in cn_news)
    assert all("S&P 500" not in item["summary"] and "S&P 500" not in item["title"] for item in cn_news)


def test_manager_real_mode_us_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "real")
    import src.core.config as config_module

    config_module._SETTINGS = None
    set_current_market(MARKET_US)
    try:
        manager = DataSourceManager(mode="real")
        assert manager.is_mock is True
        assert manager.source_name == "mock-local-us (real US source pending)"
        assert manager.indices()[0]["name"] == "S&P 500"
    finally:
        set_current_market(MARKET_CN)


def test_switch_ui_market_clears_daily_cache():
    _DAILY_UI_CACHE[("probe", "cn")] = object()
    assert switch_ui_market("美股") == MARKET_US
    assert ("probe", "cn") not in _DAILY_UI_CACHE


def test_styled_frame_attaches_symmetric_gradient():
    frame = pd.DataFrame(
        {"名称": ["a", "b", "c"], "涨跌幅": [-2.0, 0.0, 3.0], "数量": [1, 2, 3]},
    )
    styled = styled_frame(frame, gradient=["涨跌幅"])
    assert isinstance(styled, pd.io.formats.style.Styler)
    html = str(styled.to_html())
    assert "background-color" in html
    assert "row0_col1" in html and "row2_col1" in html


def test_styled_frame_plain_frame_without_gradient():
    frame = pd.DataFrame({"名称": ["a"], "数量": [1]})
    result = styled_frame(frame)
    assert isinstance(result, pd.DataFrame)


def test_distribution_figures_render_traces():
    report_frame = pd.DataFrame({"rating": ["买入", "买入", "持有"], "org": ["甲", "乙", "甲"]})
    assert isinstance(report_rating_figure(report_frame), go.Figure)

    paper_frame = pd.DataFrame(
        {"published_at": ["2025-01-02", "2024-05-06", "2025-08-09"], "source": ["arXiv", "SSRN", "arXiv"]}
    )
    paper_figure = paper_distribution_figure(paper_frame)
    assert isinstance(paper_figure, go.Figure)
    assert len(paper_figure.data) == 2

    strategy_frame = pd.DataFrame({"status": ["可用", "草稿"], "interface_type": ["统一接口", "统一接口"]})
    assert len(strategy_stat_figure(strategy_frame).data) == 2

    model_frame = pd.DataFrame({"level": ["fast", "deep"], "purpose": [["chat"], ["chat", "analysis"]]})
    model_figure = model_stat_figure(model_frame)
    assert len(model_figure.data) == 2


def test_distribution_figures_empty_inputs():
    assert report_rating_figure(pd.DataFrame()).data == ()
    assert paper_distribution_figure(None).data == ()


def test_page_service_methods_return_triples():
    service = FrontendService()
    status, frame, figure = service.research_reports_page("", "")
    assert isinstance(status, str) and "研报" in status
    assert isinstance(frame, pd.DataFrame)
    assert isinstance(figure, go.Figure)

    paper_status, paper_frame, paper_figure = service.paper_search_page("", "", None, None)
    assert "论文" in paper_status
    assert isinstance(paper_figure, go.Figure)

    strategy_frame, strategy_figure = service.strategies_with_stats("")
    assert isinstance(strategy_frame, pd.DataFrame)
    assert isinstance(strategy_figure, go.Figure)

    model_frame, model_figure = service.models_with_stats()
    assert isinstance(model_frame, pd.DataFrame)
    assert isinstance(model_figure, go.Figure)


def test_i18n_dictionary_and_js_injection():
    from src.frontend.i18n import TECHNICAL_TEXT_LABELS, TRANSLATIONS, technical_texts_json, translations_json

    assert len(TRANSLATIONS) >= 300
    assert TECHNICAL_TEXT_LABELS["change_pct"] == {"zh": "涨跌幅", "en": "Change %"}
    payload = json.loads(translations_json())
    assert payload
    technical_payload = json.loads(technical_texts_json())
    assert technical_payload["updated_at"]["zh"] == "更新时间"
    distinct = sum(1 for source, target in payload.items() if source != target)
    assert distinct >= len(payload) * 0.9

    from src.frontend.app import APP_JS

    assert "__I18N_DICT__" not in APP_JS
    assert "__I18N_TECHNICAL_TEXTS__" not in APP_JS
    assert "I18N_TECHNICAL_TEXTS" in APP_JS
    assert "TECH_EN_TO_ZH" in APP_JS
    assert "all-in-one-ui-lang" in APP_JS
    assert "all-in-one-ui-market" in APP_JS
    assert 'const LANG_MARKET = { zh: "cn", en: "us" }' in APP_JS
    assert 'applyMarketSelection("cn", { syncLanguage: true })' in APP_JS
    assert "applyLanguage(storedLang, { syncMarket: true })" in APP_JS


def test_header_html_contains_toggle_controls():
    from src.frontend.header import header_html

    html = header_html()
    assert "app-language-toggle" in html
    assert "app-market-cn" in html
    assert "app-market-us" in html


def test_i18n_translator_round_trip():
    from src.frontend.i18n import translate, translate_technical

    assert translate("首页") in {"首页", "Home"}
    if translate("首页") == "Home":
        assert translate("Home") == "Home"
    assert translate("正常") == "Normal"
    assert translate_technical("change_pct", "zh") == "涨跌幅"
    assert translate_technical("change_pct", "en") == "Change %"
    assert translate_technical("unknown_field", "zh") == "unknown_field"


def test_app_config_contains_market_switcher_and_new_plots(client):
    responses = [
        client.get("/app/research/config"),
        client.get("/app/strategy/config"),
        client.get("/app/admin/config"),
    ]
    assert all(response.status_code == 200 for response in responses)
    payloads = [response.json() for response in responses]
    components = [component for payload in payloads for component in payload["components"]]
    elem_ids = {component.get("props", {}).get("elem_id") for component in components}
    assert "market-switcher" in elem_ids
    labels = {
        component.get("props", {}).get("label") for component in components if component.get("props", {}).get("label")
    }
    assert {"研报分布", "论文分布", "策略分布", "模型分布"} <= labels
