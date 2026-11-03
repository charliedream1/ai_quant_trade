"""Validated resource uploads with visible preview and downloadable diagnostics."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.core.config import get_settings
from src.engine.market.resource_import import import_config, template_path
from src.engine.market.resource_pool import ResourcePoolService
from src.engine.market.resource_transfer import ResourceImportService, errors_csv

from .foundation import RESOURCE_POOL_COLUMNS, RESOURCE_POOL_ITEM_COLUMNS, to_frame, uploaded_file_path


def _content(value: Any) -> tuple[str, bytes]:
    path = uploaded_file_path(value)
    if path.stat().st_size > import_config()["limits"]["file_bytes"]:
        raise ValueError("文件超过资源池上传大小限制")
    return path.name, path.read_bytes()


class ResourceImportUIMixin:
    def resource_template(self, kind: str) -> str:
        return str(template_path(kind))

    def resource_import_preview(self, pool_id: Any, value: Any, mode: str) -> tuple[Any, ...]:
        name, content = _content(value)
        service = ResourceImportService(ResourcePoolService().repo)
        report = service.preview(int(pool_id) if pool_id else None, name, content, mode)
        export = get_settings().data_dir / "exports/resource-import" / (report["sha256"] + ".csv")
        export.parent.mkdir(parents=True, exist_ok=True)
        export.write_text(errors_csv(report), encoding="utf-8")
        counts = report["counts"]
        status = f"校验{'通过' if report['valid'] else '未通过'}：新增{counts['add']}，更新{counts['update']}，跳过{counts['skip']}，错误{len(report['errors'])}。"
        warnings = report["warnings"] + [row["warning"] for row in report["rows"] if row.get("warning")]
        if warnings:
            status += "\n\n" + "；".join(dict.fromkeys(warnings))
        return status, pd.DataFrame(report["rows"]), pd.DataFrame(report["errors"]), str(export), report

    def resource_import_commit(
        self,
        pool_id: Any,
        value: Any,
        mode: str,
        allow_partial: bool,
        preview: dict[str, Any],
    ) -> tuple[Any, ...]:
        if not preview or not preview.get("preview_hash"):
            raise ValueError("请先校验预览，再确认导入")
        name, content = _content(value)
        pools = ResourcePoolService()
        result = ResourceImportService(pools.repo).commit(
            int(pool_id) if pool_id else None,
            name,
            content,
            mode=mode,
            preview_hash=preview["preview_hash"],
            allow_partial=bool(allow_partial),
        )
        return (
            f"导入完成：资源池{result['pool_id']}，新增{result['added']}，更新{result['updated']}，跳过{result['skipped']}。",
            to_frame(pools.list_pools(), RESOURCE_POOL_COLUMNS),
            to_frame(pools.list_items(result["pool_id"]), RESOURCE_POOL_ITEM_COLUMNS),
        )
