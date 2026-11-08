"""Local security master lookup and fuzzy symbol resolution."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from threading import RLock
from typing import Any

from src.core.config import get_settings
from src.core.logger import get_logger
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data.manager import MARKET_CN, MARKET_US, current_market, normalize_market
from src.data.models import STOCKS, US_STOCKS
from src.data.symbols import parse_symbol

LOG = get_logger("security_master")

SEED_FILE_NAME = "security_master.seed.csv"
TOKEN_SPLIT_PATTERN = re.compile(r"[\s,，;；、/|]+")
US_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
CN_CODE_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
SEARCH_COLUMNS = ["symbol", "market", "name", "abbr", "pinyin", "aliases", "exchange", "asset_type", "updated_at"]
MAX_SYMBOLS_PER_PARSE = 100


class SecurityMasterService:
    """Resolve user-entered codes, names, aliases, and pinyin into canonical symbols."""

    _seed_lock = RLock()
    _seeded_db_paths: set[Path] = set()

    def __init__(self, repo: Repository | None = None, seed_path: Path | None = None) -> None:
        self.repo = repo or Repository()
        self.seed_path = seed_path or get_settings().project_root / "egs/examples/data" / SEED_FILE_NAME
        self.ensure_seeded()

    def ensure_seeded(self) -> None:
        db_path = Path(getattr(self.repo.db, "db_path", ":memory:"))
        with self._seed_lock:
            if db_path in self._seeded_db_paths and self._row_count() > 0:
                return
            if self._row_count() > 0:
                self._seeded_db_paths.add(db_path)
                return
            rows = self._seed_rows()
            if not rows:
                return
            now = utc_now_iso()
            self.repo.db.executemany(
                """
                INSERT INTO security_master
                    (symbol, market, name, abbr, pinyin, aliases, exchange, asset_type, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, market) DO UPDATE SET
                    name = excluded.name,
                    abbr = excluded.abbr,
                    pinyin = excluded.pinyin,
                    aliases = excluded.aliases,
                    exchange = excluded.exchange,
                    asset_type = excluded.asset_type,
                    is_active = excluded.is_active,
                    updated_at = excluded.updated_at
                """,
                [
                    (
                        row["symbol"],
                        row["market"],
                        row["name"],
                        row.get("abbr", ""),
                        row.get("pinyin", ""),
                        row.get("aliases", ""),
                        row.get("exchange", ""),
                        row.get("asset_type", "stock") or "stock",
                        int(row.get("is_active", 1) or 1),
                        row.get("updated_at") or now,
                    )
                    for row in rows
                ],
            )
            self._seeded_db_paths.add(db_path)
            LOG.info("security master seeded | rows={} seed={}", len(rows), self.seed_path)

    def search(self, query: Any = "", market: Any = None, limit: int = 20) -> list[dict[str, Any]]:
        text = _normalize_query(query)
        selected_market = _normalize_optional_market(market)
        row_limit = max(1, min(int(limit or 20), 100))
        if not text:
            return self._recent_rows(selected_market, row_limit)
        direct = self._direct_symbol_row(text, selected_market)
        rows: list[dict[str, Any]] = []
        if direct:
            rows.append(direct)
        pattern = f"%{text.lower()}%"
        params: list[Any] = [pattern, pattern, pattern, pattern]
        market_clause = ""
        if selected_market:
            market_clause = " AND market = ?"
            params.append(selected_market)
        params.append(row_limit * 3)
        matched = self.repo.db.query(
            f"""
            SELECT {", ".join(SEARCH_COLUMNS)}
              FROM security_master
             WHERE is_active = 1
               AND (
                    lower(symbol) LIKE ?
                 OR lower(name) LIKE ?
                 OR lower(abbr) LIKE ?
                 OR lower(pinyin) LIKE ?
                 OR aliases LIKE '%' || ? || '%'
               )
               {market_clause}
             ORDER BY
                 CASE
                     WHEN lower(symbol) = ? THEN 0
                     WHEN name = ? THEN 1
                     WHEN lower(abbr) = ? THEN 2
                     WHEN lower(symbol) LIKE ? THEN 3
                     ELSE 4
                 END,
                 market ASC,
                 symbol ASC
             LIMIT ?
            """,
            (
                *params[:4],
                text,
                *params[4:-1],
                text.lower(),
                text,
                text.upper(),
                f"{text.lower()}%",
                params[-1],
            ),
        )
        rows.extend(matched)
        return _dedupe_rows(rows)[:row_limit]

    def resolve(self, value: Any, market: Any = None) -> dict[str, Any] | None:
        text = _normalize_query(value)
        if not text:
            return None
        selected_market = _normalize_optional_market(market)
        direct = self._direct_symbol_row(text, selected_market)
        if direct:
            return direct
        rows = self.search(text, selected_market, limit=1)
        return rows[0] if rows else None

    def resolve_symbol(self, value: Any, market: Any = None) -> str:
        row = self.resolve(value, market)
        if row:
            return str(row["symbol"])
        text = _normalize_query(value)
        selected_market = _normalize_optional_market(market) or current_market()
        if selected_market == MARKET_US and US_TICKER_PATTERN.fullmatch(text.upper()):
            return text.upper()
        return ""

    def parse_symbols(self, value: Any, market: Any = None, limit: int = MAX_SYMBOLS_PER_PARSE) -> list[str]:
        tokens = _extract_tokens(value)
        selected_market = _normalize_optional_market(market)
        symbols: list[str] = []
        for token in tokens:
            for code in CN_CODE_PATTERN.findall(token):
                resolved = self.resolve_symbol(code, selected_market)
                if resolved and resolved not in symbols:
                    symbols.append(resolved)
            if CN_CODE_PATTERN.fullmatch(token):
                continue
            resolved = self.resolve_symbol(token, selected_market)
            if resolved and resolved not in symbols:
                symbols.append(resolved)
            if len(symbols) >= limit:
                break
        return symbols[:limit]

    def _row_count(self) -> int:
        return int(self.repo.db.scalar("SELECT COUNT(*) FROM security_master") or 0)

    def _recent_rows(self, market: str | None, limit: int) -> list[dict[str, Any]]:
        if market:
            return self.repo.db.query(
                f"""
                SELECT {", ".join(SEARCH_COLUMNS)}
                  FROM security_master
                 WHERE is_active = 1 AND market = ?
                 ORDER BY updated_at DESC, symbol ASC
                 LIMIT ?
                """,
                (market, limit),
            )
        return self.repo.db.query(
            f"""
            SELECT {", ".join(SEARCH_COLUMNS)}
              FROM security_master
             WHERE is_active = 1
             ORDER BY market ASC, symbol ASC
             LIMIT ?
            """,
            (limit,),
        )

    def _direct_symbol_row(self, text: str, market: str | None) -> dict[str, Any] | None:
        if market != MARKET_US:
            try:
                parsed = parse_symbol(text, stock_only=False)
                if market and market == MARKET_CN:
                    return self._row_by_symbol(parsed.code, MARKET_CN)
                return self._row_by_symbol(parsed.code, MARKET_CN) or _row_from_symbol(
                    parsed.code,
                    MARKET_CN,
                    parsed.market,
                )
            except ValueError:
                pass
        if market != MARKET_CN and US_TICKER_PATTERN.fullmatch(text.upper()):
            symbol = text.upper()
            return self._row_by_symbol(symbol, MARKET_US) or _row_from_symbol(symbol, MARKET_US, "")
        return None

    def _row_by_symbol(self, symbol: str, market: str) -> dict[str, Any] | None:
        return self.repo.db.query_one(
            f"""
            SELECT {", ".join(SEARCH_COLUMNS)}
              FROM security_master
             WHERE symbol = ? AND market = ? AND is_active = 1
             LIMIT 1
            """,
            (symbol, market),
        )

    def _seed_rows(self) -> list[dict[str, Any]]:
        rows = self._seed_file_rows()
        rows.extend(_rows_from_models(STOCKS, MARKET_CN))
        rows.extend(_rows_from_models(US_STOCKS, MARKET_US))
        return _dedupe_rows(rows)

    def _seed_file_rows(self) -> list[dict[str, Any]]:
        if not self.seed_path.exists():
            LOG.warning("security master seed file missing | path={}", self.seed_path)
            return []
        with self.seed_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [_normalize_seed_row(row) for row in reader if row.get("symbol") and row.get("name")]


def parse_security_symbols(value: Any, market: Any = None, limit: int = MAX_SYMBOLS_PER_PARSE) -> list[str]:
    """Parse one or many user-entered securities into canonical symbols."""

    return SecurityMasterService().parse_symbols(value, market=market, limit=limit)


def resolve_security_symbol(value: Any, market: Any = None) -> str:
    """Resolve a single user-entered security into a canonical symbol."""

    return SecurityMasterService().resolve_symbol(value, market=market)


def _extract_tokens(value: Any) -> list[str]:
    values: list[Any] = []
    if value is None:
        return []
    if hasattr(value, "columns") and hasattr(value, "to_dict"):
        preferred = [
            column
            for column in ("代码", "symbol", "标的代码", "证券代码", "名称", "name", "股票名称", "证券名称")
            if column in value.columns
        ]
        if preferred:
            for column in preferred:
                values.extend(value[column].dropna().tolist())
        else:
            values.extend(value.astype(str).to_numpy().flatten().tolist())
    elif isinstance(value, dict):
        headers = value.get("headers") or value.get("columns") or []
        data = value.get("data") or value.get("values") or []
        if headers and data:
            try:
                import pandas as pd

                values.extend(_extract_tokens(pd.DataFrame(data, columns=headers)))
            except Exception:  # noqa: BLE001
                values.extend(data)
        else:
            values.extend(value.values())
    elif isinstance(value, list):
        for item in value:
            values.extend(_extract_tokens(item) if isinstance(item, (list, tuple, dict)) else [item])
    else:
        values.append(value)

    tokens: list[str] = []
    for item in values:
        text = _normalize_query(item)
        if not text:
            continue
        parts = [part for part in TOKEN_SPLIT_PATTERN.split(text) if part]
        if parts:
            tokens.extend(parts)
        else:
            tokens.append(text)
    return tokens


def _normalize_seed_row(row: dict[str, Any]) -> dict[str, Any]:
    market = _normalize_optional_market(row.get("market")) or current_market()
    symbol = str(row.get("symbol") or "").strip().upper()
    if market == MARKET_CN:
        try:
            symbol = parse_symbol(symbol, stock_only=False).code
        except ValueError:
            pass
    return {
        "symbol": symbol,
        "market": market,
        "name": str(row.get("name") or "").strip(),
        "abbr": str(row.get("abbr") or "").strip().upper(),
        "pinyin": str(row.get("pinyin") or "").strip().lower(),
        "aliases": str(row.get("aliases") or "").strip(),
        "exchange": str(row.get("exchange") or "").strip().upper(),
        "asset_type": str(row.get("asset_type") or "stock").strip() or "stock",
        "is_active": int(row.get("is_active", 1) or 1),
    }


def _rows_from_models(items: dict[str, dict[str, Any]], market: str) -> list[dict[str, Any]]:
    return [
        {
            "symbol": str(symbol).upper() if market == MARKET_US else str(symbol),
            "market": market,
            "name": str(item.get("name") or symbol),
            "abbr": str(symbol).upper(),
            "pinyin": "",
            "aliases": "",
            "exchange": str(item.get("market") or ""),
            "asset_type": "stock",
            "is_active": 1,
        }
        for symbol, item in items.items()
    ]


def _row_from_symbol(symbol: str, market: str, exchange: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "market": market,
        "name": symbol,
        "abbr": symbol.upper(),
        "pinyin": "",
        "aliases": "",
        "exchange": exchange,
        "asset_type": "stock",
        "updated_at": utc_now_iso(),
    }


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        symbol = str(row.get("symbol") or "").strip()
        market = str(row.get("market") or "").strip()
        if not symbol or not market:
            continue
        key = (symbol, market)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _normalize_optional_market(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return normalize_market(value)


def _normalize_query(value: Any) -> str:
    return str(value or "").strip()
