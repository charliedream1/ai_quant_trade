"""Generic SQLite repository helpers."""

import json
import re
from collections.abc import Sequence
from typing import Any

from .database import Database
from .exceptions import BusinessError, ErrorCode


class Repository:
    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()
        self._column_cache: dict[str, set[str]] = {}

    def _table(self, table: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise BusinessError(ErrorCode.INVALID_PARAM, "非法数据表标识")
        return table

    def _columns(self, table: str, keys) -> None:
        table = self._table(table)
        if table not in self._column_cache:
            self._column_cache[table] = {row["name"] for row in self.db.query(f"PRAGMA table_info({table})")}
        if not set(keys) <= self._column_cache[table]:
            raise BusinessError(ErrorCode.INVALID_PARAM, "数据字段不在允许范围内")

    def _order(self, table: str, value: str) -> str:
        names = []
        for item in value.split(","):
            parts = item.strip().split()
            if len(parts) not in {1, 2} or len(parts) == 2 and parts[1].upper() not in {"ASC", "DESC"}:
                raise BusinessError(ErrorCode.INVALID_PARAM, "非法排序字段")
            names.append(parts[0])
        self._columns(table, names)
        return value

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        table = self._table(table)
        keys = list(values.keys())
        self._columns(table, keys)
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})"
        cursor = self.db.execute(sql, [self._serialize(values[k]) for k in keys])
        row_id = cursor.lastrowid
        if row_id is None:
            raise BusinessError(ErrorCode.UNKNOWN, "新增记录失败")
        return self.get(table, row_id)

    def get(self, table: str, row_id: int) -> dict[str, Any]:
        row = self.db.query_one(f"SELECT * FROM {self._table(table)} WHERE id = ?", (row_id,))
        if not row:
            raise BusinessError(ErrorCode.NOT_FOUND, "资源不存在")
        return row

    def get_optional(self, table: str, row_id: int) -> dict[str, Any] | None:
        return self.db.query_one(f"SELECT * FROM {self._table(table)} WHERE id = ?", (row_id,))

    def update(self, table: str, row_id: int, values: dict[str, Any]) -> dict[str, Any]:
        if not values:
            return self.get(table, row_id)
        keys = list(values.keys())
        self._columns(table, keys)
        sets = ", ".join([f"{key} = ?" for key in keys])
        params = [self._serialize(values[k]) for k in keys] + [row_id]
        self.db.execute(f"UPDATE {self._table(table)} SET {sets} WHERE id = ?", params)
        return self.get(table, row_id)

    def delete(self, table: str, row_id: int) -> None:
        cursor = self.db.execute(f"DELETE FROM {self._table(table)} WHERE id = ?", (row_id,))
        if cursor.rowcount == 0:
            raise BusinessError(ErrorCode.NOT_FOUND, "资源不存在")

    def list(
        self,
        table: str,
        where: str = "",
        params: Sequence[Any] = (),
        order_by: str = "id DESC",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {self._table(table)}"
        if where:
            sql += " WHERE " + where
        if order_by:
            sql += " ORDER BY " + self._order(table, order_by)
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return self.db.query(sql, params)

    def page(
        self,
        table: str,
        page: int = 1,
        page_size: int = 20,
        where: str = "",
        params: Sequence[Any] = (),
        order_by: str = "id DESC",
    ) -> dict[str, Any]:
        page = max(int(page or 1), 1)
        page_size = min(max(int(page_size or 20), 1), 100)
        sql_where = (" WHERE " + where) if where else ""
        table = self._table(table)
        total = self.db.scalar(f"SELECT COUNT(*) AS cnt FROM {table}{sql_where}", params) or 0
        offset = (page - 1) * page_size
        rows = self.db.query(
            f"SELECT * FROM {table}{sql_where} ORDER BY {self._order(table, order_by)} LIMIT ? OFFSET ?",
            tuple(params) + (page_size, offset),
        )
        return {"items": rows, "page": page, "page_size": page_size, "total": total}

    def exists(self, table: str, row_id: int) -> bool:
        return bool(self.db.scalar(f"SELECT COUNT(*) AS cnt FROM {self._table(table)} WHERE id = ?", (row_id,)))

    def _serialize(self, value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return value


def json_loads(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def make_where(parts: list[tuple[str, Any]]) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for clause, value in parts:
        if value is None or value == "":
            continue
        clauses.append(clause)
        if isinstance(value, (tuple, list)):
            params.extend(list(value))
        else:
            params.append(value)
    return " AND ".join(clauses), params
