"""Read-only import previews and atomic optimistic commits."""

from __future__ import annotations

import csv
import hashlib
import json
from io import StringIO
from typing import Any

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.data import current_market

from .resource_import import import_config, parse_import


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def errors_csv(report: dict[str, Any]) -> str:
    stream = StringIO()
    writer = csv.writer(stream)
    columns = ["row", "field", "value", "message"]
    writer.writerow(columns)
    for error in report.get("errors", []):
        values = [str(error.get(key, "")) for key in columns]
        writer.writerow(["'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])
    return "\ufeff" + stream.getvalue()


class ResourceImportService:
    def __init__(self, repo: Repository):
        self.repo = repo

    def _target(self, pool_id: int | None) -> tuple[int | None, str, list[dict[str, Any]]]:
        if pool_id is not None and pool_id <= 0:
            raise ValueError("资源池ID必须为正数")
        pool = (
            self.repo.get("resource_pools", pool_id)
            if pool_id
            else self.repo.db.query_one("SELECT * FROM resource_pools ORDER BY updated_at DESC, id DESC LIMIT 1")
        )
        identifier = int(pool["id"]) if pool else None
        items = self.repo.list("resource_pool_items", "pool_id = ?", (identifier,), order_by="id") if pool else []
        return identifier, _digest([pool, items]), items

    def preview(self, pool_id: int | None, filename: str, content: bytes, mode: str = "merge") -> dict[str, Any]:
        if mode not in {"merge", "skip"}:
            raise ValueError("冲突模式仅支持 merge/skip")
        market = current_market()
        report = parse_import(filename, content, self.repo, market)
        identifier, revision, items = self._target(pool_id)
        existing = {str(row["symbol"]): row for row in items}
        if {str(row["market"]) for row in items} - {market}:
            report["errors"].append(
                {"row": 0, "field": "market", "value": market, "message": "目标资源池含其他市场，请分池导入"}
            )
        for row in report["rows"]:
            row["action"] = ("skip" if mode == "skip" else "update") if row["symbol"] in existing else "add"
        report.update(
            {
                "pool_id": identifier,
                "revision": revision,
                "mode": mode,
                "market": market,
                "schema_digest": _digest(import_config()),
                "valid": not report["errors"],
                "counts": {
                    action: sum(row["action"] == action for row in report["rows"])
                    for action in ("add", "update", "skip")
                },
            }
        )
        report["preview_hash"] = _digest(
            [
                report["sha256"],
                revision,
                report["schema_digest"],
                market,
                mode,
            ]
        )
        return report

    def commit(
        self,
        pool_id: int | None,
        filename: str,
        content: bytes,
        *,
        mode: str = "merge",
        preview_hash: str = "",
        allow_partial: bool = False,
    ) -> dict[str, Any]:
        with self.repo.db.transaction():
            report = self.preview(pool_id, filename, content, mode)
            if preview_hash and preview_hash != report["preview_hash"]:
                raise ValueError("文件、目标池或配置已变化，请重新校验预览")
            global_errors = [row for row in report["errors"] if row["row"] == 0]
            if global_errors or report["errors"] and not allow_partial or not report["rows"]:
                problems = "；".join(f"第{row['row']}行：{row['message']}" for row in report["errors"])
                raise ValueError(f"导入校验未通过：{problems}")
            identifier = report["pool_id"] or self._create_default()
            for row in report["rows"]:
                if row["action"] != "skip":
                    self._write(identifier, row)
            self.repo.update("resource_pools", identifier, {"updated_at": utc_now_iso()})
            return {
                "pool_id": identifier,
                "file_name": report["file_name"],
                "sha256": report["sha256"],
                "added": report["counts"]["add"],
                "updated": report["counts"]["update"],
                "skipped": report["counts"]["skip"] + len(report["errors"]),
                "errors": report["errors"],
                "warnings": report["warnings"],
                "schema_version": report["schema_version"],
            }

    def _create_default(self) -> int:
        now = utc_now_iso()
        return int(
            self.repo.insert(
                "resource_pools",
                {
                    "name": "默认资源池",
                    "description": "通过文件导入创建",
                    "source_type": "import",
                    "created_at": now,
                    "updated_at": now,
                },
            )["id"]
        )

    def _write(self, pool_id: int, row: dict[str, Any]) -> None:
        now = utc_now_iso()
        existing = self.repo.db.query_one(
            "SELECT id FROM resource_pool_items WHERE pool_id = ? AND symbol = ?", (pool_id, row["symbol"])
        )
        values = {key: row.get(key, "") for key in ("market", "name", "weight", "tags", "remark", "source")}
        values["updated_at"] = now
        if existing:
            self.repo.update("resource_pool_items", int(existing["id"]), values)
        else:
            self.repo.insert(
                "resource_pool_items", {**values, "pool_id": pool_id, "symbol": row["symbol"], "created_at": now}
            )
