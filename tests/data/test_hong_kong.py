"""Hong Kong identities, isolation and request routing without external network."""

import pytest

from src.data import DataSourceManager, normalize_market
from src.data.hong_kong import hk_symbol
from src.data.security_master import SecurityMasterService
from src.data.symbols import parse_symbol


@pytest.mark.parametrize("value", ["00700", "00700.HK", "HK00700", "700.HK"])
def test_hong_kong_identity_preserves_leading_zeros(value):
    assert hk_symbol(value) == "00700.HK"
    assert parse_symbol(value).secid == "116.00700"


@pytest.mark.parametrize("value", ["600519", "000001.SZ", "HK00700.SH", "00000.HK", "80700.HK"])
def test_hk_does_not_reinterpret_mainland_or_conflicting_codes(value):
    with pytest.raises(ValueError):
        hk_symbol(value)


def test_hk_aliases_and_explicit_development_source():
    assert normalize_market("港股") == "HK"
    data = DataSourceManager(mode="mock", market="HK")
    quote = data.stock_quote("00700")
    assert data.is_mock and quote["currency"] == "HKD" and quote["symbol"] == "00700.HK"
    assert quote["data_source"] == "mock-local-hk"
    with pytest.raises(ValueError):
        normalize_market("unsupported-market")


def test_hk_http_context_and_security_lookup(client):
    quote = client.get("/api/v1/stocks/00700.HK/detail", headers={"x-aiquant-market": "HK"}).json()
    assert quote["code"] == 0 and quote["data"]["quote"]["currency"] == "HKD"
    master = SecurityMasterService()
    assert master.resolve_symbol("腾讯", "HK") == "00700.HK"
    assert master.resolve_symbol("00700.HK", "CN") == ""
    result = client.get("/api/v1/market/indices", headers={"x-aiquant-market": "HK"}).json()
    assert result["code"] == 0 and result["data"] == []


def test_watchlists_keep_markets_separate(client):
    from src.engine.market.quote_service import QuoteService

    hk = QuoteService(data=DataSourceManager(mode="mock", market="HK"))
    cn = QuoteService(data=DataSourceManager(mode="mock", market="CN"))
    group = hk.create_group("Cross-market isolation")
    hk.add_symbols(group["id"], ["00700"])
    cn.add_symbols(group["id"], ["600519"])
    assert [row["symbol"] for row in hk.watchlist_quotes(group["id"])] == ["00700.HK"]
    assert [row["symbol"] for row in cn.watchlist_quotes(group["id"])] == ["600519"]


def test_hk_cli_header_is_forwarded_and_does_not_change_default(cli_command, client):
    from src.data import current_market, set_current_market

    before = current_market()
    try:
        set_current_market("CN")
        result = cli_command("--market", "HK", "stock", "show", "00700.HK", "--format", "json")
        assert result["data"]["quote"]["currency"] == "HKD"
        assert current_market() == "CN"
    finally:
        set_current_market(before)
