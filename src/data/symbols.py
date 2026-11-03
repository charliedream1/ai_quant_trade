"""Strict A-share ticker parsing and market routing."""

from __future__ import annotations

import re
from dataclasses import dataclass

SH_INDEX_CODES = {"000010", "000016", "000300", "000688", "000852", "000905"}
LEGACY_BEIJING_PREFIXES = ("43", "83", "87")
_TICKER = re.compile(r"^(?:(sh|sz|bj)(\d{6})|(\d{6})(?:\.(sh|sz|bj))?)$", re.IGNORECASE)


@dataclass(frozen=True)
class SecuritySymbol:
    code: str
    market: str

    @property
    def prefix(self) -> str:
        return self.market.lower()

    @property
    def qualified(self) -> str:
        return f"{self.prefix}{self.code}"

    @property
    def secid(self) -> str:
        return f"{1 if self.market == 'SH' else 0}.{self.code}"

    @property
    def cache_key(self) -> str:
        return f"{self.market}:{self.code}"

    @property
    def is_legacy_beijing(self) -> bool:
        return self.code.startswith(LEGACY_BEIJING_PREFIXES)


def parse_symbol(value: str, *, stock_only: bool = False) -> SecuritySymbol:
    raw = str(value or "").strip()
    matched = _TICKER.fullmatch(raw)
    if not matched:
        raise ValueError(
            f"无法解析证券代码 {value!r}；支持 600519、SH600519、600519.SH、BJ920982，市场前缀和后缀不能同时使用"
        )

    code = matched.group(2) or matched.group(3)
    explicit = (matched.group(1) or matched.group(4) or "").upper()
    natural = _natural_market(code)
    if explicit:
        if code.startswith("000"):
            if explicit == "BJ":
                raise ValueError(f"{value!r} 的市场标识与 000xxx 号段矛盾")
        elif explicit != natural:
            raise ValueError(f"{value!r} 的市场标识错误：{code} 属于 {natural} 市场")
    market = explicit or ("SH" if code in SH_INDEX_CODES else natural)
    if stock_only and market == "SH" and code.startswith("000"):
        raise ValueError(f"{value!r} 指向沪市指数；个股接口请使用明确的深市代码，如 SZ{code}")
    return SecuritySymbol(code=code, market=market)


def _natural_market(code: str) -> str:
    if code.startswith("92") or code.startswith(LEGACY_BEIJING_PREFIXES):
        return "BJ"
    if code.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"
