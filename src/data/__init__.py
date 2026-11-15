"""Compatible domain exports loaded only when requested."""

from importlib import import_module

EXPORTS = {
    "ETFUniverseService": (".etf", "ETFUniverseService"),
    "MARKET_CN": (".manager", "MARKET_CN"),
    "MARKET_HK": (".manager", "MARKET_HK"),
    "MARKET_US": (".manager", "MARKET_US"),
    "DataSourceManager": (".manager", "DataSourceManager"),
    "current_market": (".manager", "current_market"),
    "normalize_market": (".manager", "normalize_market"),
    "set_current_market": (".manager", "set_current_market"),
    "SecurityMasterService": (".security_master", "SecurityMasterService"),
    "parse_security_symbols": (".security_master", "parse_security_symbols"),
    "resolve_security_symbol": (".security_master", "resolve_security_symbol"),
}

__all__ = [
    "MARKET_CN",
    "MARKET_HK",
    "MARKET_US",
    "DataSourceManager",
    "SecurityMasterService",
    "current_market",
    "normalize_market",
    "parse_security_symbols",
    "resolve_security_symbol",
    "set_current_market",
    "ETFUniverseService",
]


def __getattr__(name):
    if name not in EXPORTS:
        raise AttributeError(name)
    module, symbol = EXPORTS[name]
    value = getattr(import_module(module, __name__), symbol)
    globals()[name] = value
    return value
