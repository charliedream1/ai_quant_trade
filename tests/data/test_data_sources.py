import uuid
from types import SimpleNamespace

import pytest
from loguru import logger

import src.data.eastmoney as eastmoney
from src.data.eastmoney import EastmoneyDataSource
from src.data.security_master import SecurityMasterService, parse_security_symbols
from src.data.symbols import parse_symbol


@pytest.mark.parametrize(
    ("raw", "code", "market", "secid"),
    [
        ("600519", "600519", "SH", "1.600519"),
        ("600519.SH", "600519", "SH", "1.600519"),
        ("sz000001", "000001", "SZ", "0.000001"),
        ("000016", "000016", "SH", "1.000016"),
        ("SZ000016", "000016", "SZ", "0.000016"),
        ("BJ920982", "920982", "BJ", "0.920982"),
        ("832982", "832982", "BJ", "0.832982"),
        ("510300", "510300", "SH", "1.510300"),
    ],
)
def test_symbol_normalization_preserves_market(raw, code, market, secid):
    parsed = parse_symbol(raw)
    assert (parsed.code, parsed.market, parsed.secid) == (code, market, secid)


@pytest.mark.parametrize("raw", ["foo600519bar", "6005190", "SH600519.SZ", "SZ600519", "BJ000001"])
def test_symbol_normalization_rejects_ambiguous_or_conflicting_input(raw):
    with pytest.raises(ValueError):
        parse_symbol(raw)


def test_stock_only_rejects_shanghai_index_but_allows_explicit_shenzhen_stock():
    with pytest.raises(ValueError):
        parse_symbol("000016", stock_only=True)
    assert parse_symbol("SZ000016", stock_only=True).market == "SZ"


def test_security_master_resolves_code_name_alias_and_pinyin(tmp_path, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "security_master.db"))
    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))

    import src.core.config as config_module
    from src.core.database import Database

    config_module._SETTINGS = None
    Database.reset_instance()
    try:
        service = SecurityMasterService()

        assert service.resolve_symbol("贵州茅台") == "600519"
        assert service.resolve_symbol("茅台") == "600519"
        assert service.resolve_symbol("ningdeshidai") == "300750"
        assert service.resolve_symbol("英伟达") == "NVDA"
        assert parse_security_symbols("贵州茅台, 宁德, AAPL") == ["600519", "300750", "AAPL"]
    finally:
        Database.reset_instance()
        config_module._SETTINGS = None


def test_forced_refresh_bypasses_fresh_cache():
    key = f"forced:{uuid.uuid4()}"
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return {"version": calls}

    try:
        assert eastmoney._cached(key, 300, "test", "provider", loader)["version"] == 1
        assert eastmoney._cached(key, 300, "test", "provider", loader)["version"] == 1
        assert eastmoney._cached(key, 300, "test", "provider", loader, force_refresh=True)["version"] == 2
        assert calls == 2
    finally:
        with eastmoney._CACHE_LOCK:
            eastmoney._CACHE.pop(key, None)
            eastmoney._RETRY_AFTER.pop(key, None)


def test_http_session_uses_market_network_settings(monkeypatch):
    monkeypatch.setattr(
        eastmoney,
        "get_settings",
        lambda: SimpleNamespace(
            data_http_trust_env=False,
            data_http_retries=2,
            data_http_backoff_seconds=0.0,
        ),
    )

    session = eastmoney._session()

    assert session.trust_env is False
    assert session.adapters["https://"].max_retries.total == 2
    assert session.adapters["https://"].max_retries.status == 2
    assert session.adapters["https://"].max_retries.connect == 0
    assert session.adapters["https://"].max_retries.read == 0
    assert session.adapters["http://"].max_retries.total == 2


def test_market_cache_ttl_is_capped_by_global_setting(monkeypatch):
    monkeypatch.setattr(eastmoney, "get_settings", lambda: SimpleNamespace(data_cache_ttl_seconds=120))

    assert eastmoney._market_cache_ttl(15, 300) <= 120


def test_http_get_emits_data_source_log(monkeypatch):
    class FakeResponse:
        status_code = 200

    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(eastmoney._HTTP, "get", fake_get)
    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(str(message)),
        format="{extra[module]}|{level.name}|{message}",
        level="DEBUG",
    )
    try:
        response = eastmoney._http_get("https://qt.gtimg.cn/q=sh600519", timeout=1)
        logger.complete()
    finally:
        logger.remove(sink_id)

    assert response.status_code == 200
    assert calls and calls[0][1]["timeout"] == 1
    joined = "\n".join(messages)
    assert "data.source|DEBUG|market data request completed" in joined
    assert "provider=tencent-qt" in joined
    assert "host=qt.gtimg.cn" in joined
    assert "status=200" in joined


def test_http_get_proxy_error_logs_without_traceback(monkeypatch):
    def fake_get(_url, **_kwargs):
        raise eastmoney.requests.exceptions.ProxyError("proxy closed connection\nsecond line")

    monkeypatch.setattr(eastmoney._HTTP, "get", fake_get)
    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(str(message)),
        format="{extra[module]}|{level.name}|{message}",
        level="DEBUG",
    )
    try:
        with pytest.raises(eastmoney.requests.exceptions.ProxyError):
            eastmoney._http_get("https://qt.gtimg.cn/q=sh600519", timeout=1)
        logger.complete()
    finally:
        logger.remove(sink_id)

    joined = "\n".join(messages)
    assert "data.source|WARNING|market data request failed" in joined
    assert "error_type=ProxyError" in joined
    assert "reason=代理连接失败" in joined
    assert "trust_env=" in joined
    assert "retries=" in joined
    assert "Traceback" not in joined


def test_quote_prefers_tencent_and_does_not_call_fallbacks(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = {"symbol": "600519", "data_source": "tencent-qt"}
    monkeypatch.setattr(provider, "_load_stock_quote_tencent", lambda symbol: calls.append("tencent") or expected)
    monkeypatch.setattr(provider, "_load_stock_quote_sina", lambda symbol: calls.append("sina"))
    monkeypatch.setattr(provider, "_load_stock_quote_eastmoney", lambda symbol: calls.append("eastmoney"))

    assert provider._load_stock_quote(parse_symbol("600519")) == expected
    assert calls == ["tencent"]


def test_quote_uses_sina_before_eastmoney(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = {"symbol": "600519", "data_source": "sina-hq"}

    def fail_tencent(symbol):
        calls.append("tencent")
        raise RuntimeError("unavailable")

    monkeypatch.setattr(provider, "_load_stock_quote_tencent", fail_tencent)
    monkeypatch.setattr(provider, "_load_stock_quote_sina", lambda symbol: calls.append("sina") or expected)
    monkeypatch.setattr(provider, "_load_stock_quote_eastmoney", lambda symbol: calls.append("eastmoney"))

    assert provider._load_stock_quote(parse_symbol("600519")) == expected
    assert calls == ["tencent", "sina"]


def test_quote_uses_optional_tdx_after_tencent(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = {"symbol": "600519", "data_source": "mootdx-tdx"}

    def fail_tencent(symbol):
        calls.append("tencent")
        raise RuntimeError("unavailable")

    monkeypatch.setattr(provider, "_load_stock_quote_tencent", fail_tencent)
    monkeypatch.setattr(provider, "_load_stock_quote_tdx", lambda symbol: calls.append("tdx") or expected)
    monkeypatch.setattr(provider, "_load_stock_quote_sina", lambda symbol: calls.append("sina"))

    assert provider._load_stock_quote(parse_symbol("600519")) == expected
    assert calls == ["tencent", "tdx"]


def test_batch_quotes_only_fall_back_for_missing_symbols(monkeypatch):
    provider = EastmoneyDataSource()
    symbols = [parse_symbol("600519"), parse_symbol("000001")]
    fallback = []
    monkeypatch.setattr(
        provider,
        "_load_stock_quotes_tencent",
        lambda items: {items[0].cache_key: {"symbol": items[0].code, "data_source": "tencent-qt"}},
    )
    monkeypatch.setattr(
        provider,
        "_load_stock_quotes_sina",
        lambda items: {items[0].cache_key: {"symbol": items[0].code, "data_source": "sina-hq"}},
    )
    monkeypatch.setattr(
        provider,
        "_load_stock_quote_eastmoney",
        lambda item: fallback.append(item.code) or {"symbol": item.code, "data_source": "eastmoney-push2"},
    )

    result = provider._load_stock_quotes(symbols)
    assert [item["symbol"] for item in result] == ["600519", "000001"]
    assert [item["data_source"] for item in result] == ["tencent-qt", "sina-hq"]
    assert fallback == []


def test_batch_quotes_use_eastmoney_only_after_both_batch_sources_miss(monkeypatch):
    provider = EastmoneyDataSource()
    symbols = [parse_symbol("600519"), parse_symbol("000001")]
    fallback = []
    monkeypatch.setattr(provider, "_load_stock_quotes_tencent", lambda items: {})
    monkeypatch.setattr(
        provider,
        "_load_stock_quotes_sina",
        lambda items: {items[0].cache_key: {"symbol": items[0].code, "data_source": "sina-hq"}},
    )
    monkeypatch.setattr(
        provider,
        "_load_stock_quote_eastmoney",
        lambda item: fallback.append(item.code) or {"symbol": item.code, "data_source": "eastmoney-push2"},
    )

    result = provider._load_stock_quotes(symbols)
    assert [item["data_source"] for item in result] == ["sina-hq", "eastmoney-push2"]
    assert fallback == ["000001"]


def test_kline_falls_back_to_eastmoney_before_baostock(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = [
        {
            "date": "2026-08-28",
            "open": 10,
            "high": 12,
            "low": 9,
            "close": 11,
            "volume": 100,
            "data_source": "eastmoney-push2his",
        }
    ]

    def fail_tencent(*args):
        calls.append("tencent")
        raise RuntimeError("unavailable")

    monkeypatch.setattr(provider, "_load_kline_tencent", fail_tencent)
    monkeypatch.setattr(provider, "_load_kline_eastmoney", lambda *args: calls.append("eastmoney") or expected)
    monkeypatch.setattr(provider, "_load_kline_baostock", lambda *args: calls.append("baostock"))

    symbol = f"SH{uuid.uuid4().int % 1000000:06d}"
    assert provider._kline(symbol, "daily", 1) == expected
    assert calls == ["tencent", "eastmoney"]


def test_kline_adjustment_is_forwarded_to_loaders(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = [
        {
            "date": "2026-08-28",
            "open": 10,
            "high": 12,
            "low": 9,
            "close": 11,
            "volume": 100,
            "adjust": "hfq",
            "data_source": "eastmoney-push2his-hfq",
        }
    ]

    def fail_tencent(symbol, period, count, adjustment):
        calls.append(("tencent", adjustment))
        raise RuntimeError("unavailable")

    def load_eastmoney(symbol, period, count, adjustment):
        calls.append(("eastmoney", adjustment))
        return expected

    monkeypatch.setattr(provider, "_load_kline_tencent", fail_tencent)
    monkeypatch.setattr(provider, "_load_kline_eastmoney", load_eastmoney)
    monkeypatch.setattr(provider, "_load_kline_baostock", lambda *args: calls.append(("baostock", args[-1])))

    symbol = f"SH{uuid.uuid4().int % 1000000:06d}"
    assert provider._kline(symbol, "daily", 1, "后复权") == expected
    assert calls == [("tencent", "hfq"), ("eastmoney", "hfq")]


@pytest.mark.parametrize(
    "row",
    [
        {"date": "2026-08-28", "open": 0, "high": 12, "low": 9, "close": 11},
        {"date": "2026-08-28", "open": 10, "high": 9, "low": 8, "close": 11},
        {"date": "2026-08-28", "open": 10, "high": 12, "low": 11, "close": 9},
    ],
)
def test_kline_validation_rejects_invalid_ohlc(row):
    with pytest.raises(RuntimeError):
        EastmoneyDataSource._validate_kline([row], "test")


def test_industry_prefers_baostock_without_calling_eastmoney(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    monkeypatch.setattr(
        provider,
        "_load_stock_industry_baostock",
        lambda symbol: calls.append(("baostock", symbol)) or "白酒",
    )
    monkeypatch.setattr(provider, "_load_stock_quote_eastmoney", lambda symbol: calls.append(("eastmoney", symbol)))

    assert provider._load_stock_industry(parse_symbol("600519")) == "白酒"
    assert calls == [("baostock", "sh600519")]


def test_stock_news_falls_back_to_sina_when_eastmoney_is_empty(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = [{"title": "真实快讯", "source": "新浪7x24"}]
    monkeypatch.setattr(provider, "_load_stock_news", lambda symbol: calls.append("eastmoney") or [])
    monkeypatch.setattr(provider, "_load_stock_news_sina", lambda symbol: calls.append("sina") or expected)

    assert provider._load_stock_news_with_fallback("600519") == expected
    assert calls == ["eastmoney", "sina"]


def test_global_news_falls_back_to_sina_when_eastmoney_is_empty(monkeypatch):
    provider = EastmoneyDataSource()
    calls = []
    expected = [{"title": "真实快讯", "source": "新浪7x24"}]
    monkeypatch.setattr(provider, "_load_global_news", lambda: calls.append("eastmoney") or [])
    monkeypatch.setattr(provider, "_load_global_news_sina", lambda: calls.append("sina") or expected)

    assert provider._load_global_news_with_fallback() == expected
    assert calls == ["eastmoney", "sina"]


def test_tencent_legacy_beijing_quote_is_marked_stale():
    provider = EastmoneyDataSource()
    values = [""] * 60
    values[1] = "旧北交所代码"
    values[2] = "832982"
    values[3] = "12.50"
    values[4] = "12.50"
    values[30] = "20260830140000"
    values[31] = "0"
    values[32] = "0"
    values[35] = "0/0/0"
    values[36] = "0"
    values[38] = "0"
    values[39] = "10"
    values[44] = "1"
    values[45] = "1"
    values[46] = "1"
    values[52] = "10"

    quote = provider._parse_tencent_quote(parse_symbol("832982"), values)
    assert quote["is_stale"] is True
    assert "920xxx" in quote["stale_reason"]
