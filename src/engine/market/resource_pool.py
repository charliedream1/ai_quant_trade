"""Resource pool service for reusable research universes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.logger import get_logger
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data import DataSourceManager, current_market
from src.data.security_master import SecurityMasterService

from .resource_import import import_config
from .resource_transfer import ResourceImportService

LOG = get_logger("resource_pool")

DEFAULT_POOL_NAME = "默认资源池"
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9._-]{2,16}$")
SYMBOL_SPLIT_PATTERN = re.compile(r"[\s,，;；、]+")
SYMBOL_COLUMN_ALIASES = ("symbol", "code", "ticker", "股票代码", "证券代码", "代码", "标的")
NAME_COLUMN_ALIASES = ("name", "名称", "股票名称", "证券名称")
WEIGHT_COLUMN_ALIASES = ("weight", "权重", "目标权重")
TAGS_COLUMN_ALIASES = ("tags", "标签", "分组")
REMARK_COLUMN_ALIASES = ("remark", "备注", "说明")


class ResourcePoolService:
    """Manage user-configurable stock pools for recommendation and research workflows."""

    def __init__(self, repo: Repository | None = None, data: DataSourceManager | None = None) -> None:
        self.repo = repo or Repository()
        self.data = data or DataSourceManager()

    def list_pools(self) -> list[dict[str, Any]]:
        rows = self.repo.db.query(
            """
            SELECT p.*,
                   COUNT(i.id) AS symbol_count,
                   COALESCE(SUM(i.weight), 0) AS total_weight
              FROM resource_pools p
              LEFT JOIN resource_pool_items i ON i.pool_id = p.id
             GROUP BY p.id
             ORDER BY p.updated_at DESC, p.id DESC
            """
        )
        return rows

    def create_pool(self, name: str, description: str = "", source_type: str = "manual") -> dict[str, Any]:
        now = utc_now_iso()
        pool_name = _require_text(name, "资源池名称")
        existing = self.repo.db.query_one("SELECT id FROM resource_pools WHERE name = ?", (pool_name,))
        payload = {
            "name": pool_name,
            "description": str(description or "").strip(),
            "source_type": str(source_type or "manual").strip() or "manual",
            "updated_at": now,
        }
        if existing:
            pool = self.repo.update("resource_pools", int(existing["id"]), payload)
            LOG.info("resource pool updated | pool_id={} name={}", pool["id"], pool_name)
            return pool
        pool = self.repo.insert("resource_pools", {**payload, "created_at": now})
        LOG.info("resource pool created | pool_id={} name={}", pool["id"], pool_name)
        return pool

    def default_pool_id(self) -> int:
        row = self.repo.db.query_one("SELECT id FROM resource_pools ORDER BY updated_at DESC, id DESC LIMIT 1")
        if row:
            return int(row["id"])
        return int(self.create_pool(DEFAULT_POOL_NAME, "系统自动创建的默认资源池", "default")["id"])

    def list_items(self, pool_id: int | None = None) -> list[dict[str, Any]]:
        target_pool_id = int(pool_id or self.default_pool_id())
        return self.repo.db.query(
            """
            SELECT i.*, p.name AS pool_name
              FROM resource_pool_items i
              JOIN resource_pools p ON p.id = i.pool_id
             WHERE i.pool_id = ?
             ORDER BY i.weight DESC, i.updated_at DESC, i.id DESC
            """,
            (target_pool_id,),
        )

    def add_symbols(
        self,
        pool_id: int | None,
        symbols_text: str,
        *,
        source: str = "manual",
        remark: str = "",
        weight: float = 1.0,
    ) -> dict[str, Any]:
        symbols = parse_resource_symbols(symbols_text)
        if not symbols:
            raise ValueError("请输入有效的资源池标的代码、名称、拼音或别名")
        target_pool_id = int(pool_id or self.default_pool_id())
        rows = [
            {
                "symbol": symbol,
                "name": "",
                "weight": weight,
                "tags": "",
                "remark": remark,
                "source": source,
            }
            for symbol in symbols
        ]
        result = self._upsert_items(target_pool_id, rows)
        LOG.info(
            "resource pool symbols added | pool_id={} added={} updated={} source={}",
            target_pool_id,
            result["added"],
            result["updated"],
            source,
        )
        return result

    def import_file(self, pool_id: int | None, file_path: Path) -> dict[str, Any]:
        if file_path.stat().st_size > import_config()["limits"]["file_bytes"]:
            raise ValueError("文件超过资源池上传大小限制")
        return ResourceImportService(self.repo).commit(pool_id, file_path.name, file_path.read_bytes())

    def import_bytes(self, pool_id: int, filename: str, content: bytes) -> dict[str, Any]:
        """Parse uploads in memory; no arbitrary server paths or temporary files."""
        return ResourceImportService(self.repo).commit(pool_id, filename, content)

    def _upsert_items(self, pool_id: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
        self.repo.get("resource_pools", pool_id)
        now = utc_now_iso()
        market = current_market()
        added = 0
        updated = 0
        skipped = 0
        master = SecurityMasterService(repo=self.repo)
        for row in rows:
            resolved = master.resolve(row.get("symbol")) or master.resolve(row.get("name"))
            symbol = str((resolved or {}).get("symbol") or _normalize_symbol(row.get("symbol"))).strip()
            if not symbol:
                skipped += 1
                continue
            quote = self._quote(symbol)
            name = str(row.get("name") or (resolved or {}).get("name") or quote.get("name") or symbol).strip()
            weight = _safe_float(row.get("weight"), 1.0)
            existing = self.repo.db.query_one(
                "SELECT id FROM resource_pool_items WHERE pool_id = ? AND symbol = ?",
                (pool_id, symbol),
            )
            payload = {
                "market": str((resolved or {}).get("market") or quote.get("market") or market),
                "name": name,
                "weight": weight,
                "tags": str(row.get("tags") or "").strip(),
                "remark": str(row.get("remark") or "").strip(),
                "source": str(row.get("source") or "manual").strip() or "manual",
                "updated_at": now,
            }
            if existing:
                self.repo.update("resource_pool_items", int(existing["id"]), payload)
                updated += 1
            else:
                self.repo.insert(
                    "resource_pool_items",
                    {
                        **payload,
                        "pool_id": pool_id,
                        "symbol": symbol,
                        "created_at": now,
                    },
                )
                added += 1
        self.repo.update("resource_pools", pool_id, {"updated_at": now})
        return {"pool_id": pool_id, "added": added, "updated": updated, "skipped": skipped}

    def _quote(self, symbol: str) -> dict[str, Any]:
        try:
            return self.data.stock_quote(symbol)
        except Exception as exc:
            LOG.debug("resource pool quote lookup skipped | symbol={} error={}", symbol, exc)
            return {"symbol": symbol, "name": symbol, "market": current_market()}


def parse_resource_symbols(value: Any) -> list[str]:
    """Parse stock symbols from free text while preserving insertion order."""

    seen: set[str] = set()
    symbols: list[str] = []
    master = SecurityMasterService()
    for raw in SYMBOL_SPLIT_PATTERN.split(str(value or "")):
        symbol = master.resolve_symbol(raw) or _normalize_symbol(raw)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)
    return symbols


def _resource_rows_from_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    normalized_columns = {str(column).strip().lower(): column for column in frame.columns}
    symbol_col = _find_column(normalized_columns, SYMBOL_COLUMN_ALIASES) or frame.columns[0]
    name_col = _find_column(normalized_columns, NAME_COLUMN_ALIASES)
    weight_col = _find_column(normalized_columns, WEIGHT_COLUMN_ALIASES)
    tags_col = _find_column(normalized_columns, TAGS_COLUMN_ALIASES)
    remark_col = _find_column(normalized_columns, REMARK_COLUMN_ALIASES)
    rows: list[dict[str, Any]] = []
    master = SecurityMasterService()
    for _, item in frame.iterrows():
        raw_symbol = item.get(symbol_col)
        raw_name = item.get(name_col) if name_col else ""
        resolved = master.resolve(raw_symbol) or master.resolve(raw_name)
        symbol = str((resolved or {}).get("symbol") or _normalize_symbol(raw_symbol)).strip()
        if not symbol:
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": str(raw_name or (resolved or {}).get("name") or "").strip(),
                "weight": _safe_float(item.get(weight_col), 1.0) if weight_col else 1.0,
                "tags": str(item.get(tags_col) or "").strip() if tags_col else "",
                "remark": str(item.get(remark_col) or "").strip() if remark_col else "",
                "source": "import",
            }
        )
    return rows


def _find_column(columns: dict[str, Any], aliases: tuple[str, ...]) -> Any | None:
    for alias in aliases:
        matched = columns.get(alias.lower())
        if matched is not None:
            return matched
    return None


def _read_resource_file(file_path: Path) -> pd.DataFrame:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(file_path, encoding="gbk")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path)
    raise ValueError("资源池导入仅支持 CSV / XLSX / XLS 文件")


def _normalize_symbol(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    text = text.replace(" ", "")
    return text if SYMBOL_PATTERN.match(text) else ""


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空")
    return text
