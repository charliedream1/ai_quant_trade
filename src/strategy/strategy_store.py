"""Strategy metadata and source file store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from src.core.exceptions import BusinessError, ErrorCode
from src.core.file_storage import FileStorage
from src.core.logger import get_logger
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso

from .execution_policy import review_source, source_digest
from .loader import PROJECT_ROOT, StrategyLoader
from .validator import StrategyValidator

EXAMPLE_STRATEGY_DIR = PROJECT_ROOT / "egs" / "examples" / "strategy_examples"
EXAMPLE_INTRO_FILE = EXAMPLE_STRATEGY_DIR / "strategy_intros.yaml"
INTERFACE_LABELS = {
    "strategy_base_class": "StrategyBase 标准类",
    "class_port": "标准类端口",
    "function_port": "函数端口",
    "object_port": "对象端口",
}
StrategyExampleRows = list[dict[str, Any]]
StrategySymbols = list[str]


class StrategyStore:
    def __init__(
        self,
        repo: Repository | None = None,
        storage: FileStorage | None = None,
        validator: StrategyValidator | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.storage = storage or FileStorage()
        self.validator = validator or StrategyValidator()
        self.storage.ensure_dirs()

    def list(
        self,
        keyword: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        if keyword:
            where.append("(name LIKE ? OR description LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if status:
            mapped = {"enabled": "可用", "disabled": "停用"}.get(status, status)
            where.append("status = ?")
            params.append(mapped)
        if tag:
            where.append("tags LIKE ?")
            params.append(f"%{tag}%")
        result = self.repo.page("strategies", page, page_size, " AND ".join(where), params, order_by="updated_at DESC")
        for item in result["items"]:
            item["strategy_id"] = item["id"]
            item["tags"] = json_loads(item.get("tags"), [])
            item["default_params"] = json_loads(item.get("param_schema"), {})
        return result

    def get(self, strategy_id: int, include_code: bool = True) -> dict[str, Any]:
        row = self.repo.get("strategies", strategy_id)
        row["strategy_id"] = row["id"]
        row["tags"] = json_loads(row.get("tags"), [])
        row["default_params"] = json_loads(row.get("param_schema"), {})
        row["version_history"] = []
        if include_code:
            row["code"] = self.storage.read_text(row["file_path"])
            row["source_sha256"] = source_digest(self.storage.resolve(row["file_path"]))
            validation = self.validator.validate_source(row["code"])
            row["interface_report"] = {
                **validation,
                "validation": validation,
                "execution": "not_started",
                "entry_name": validation.get("entry_class") or validation.get("entry_func"),
            }
        return row

    def review(self, strategy_id: int, expected_sha256: str, reviewer: str):
        row = self.repo.get("strategies", strategy_id)
        return review_source(self.storage.resolve(row["file_path"]), expected_sha256, reviewer)

    def create(self, payload: dict[str, Any], origin: str = "上传") -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise BusinessError(ErrorCode.INVALID_PARAM, "策略名称不能为空")
        code = payload.get("code") or ""
        if not code and payload.get("file_path"):
            code = self.storage.read_text(payload["file_path"])
        validation = self.validator.validate_source(code)
        version = payload.get("version") or "v1"
        if self.repo.db.scalar("SELECT COUNT(*) FROM strategies WHERE name=? AND version=?", (name, version)):
            raise BusinessError(ErrorCode.CONSTRAINT_CONFLICT, "同名同版本策略已存在，请使用新版本")
        now = utc_now_iso()
        # Keep filenames short on Windows; the human name/version live in SQLite.
        filename = self.storage.safe_filename(uuid4().hex, suffix=".py")
        file_path = f"strategies/upload/{filename}"
        self.storage.write_text(file_path, code)
        params_schema = (
            payload.get("default_params") or payload.get("param_schema") or validation.get("params_schema") or {}
        )
        row = self.repo.insert(
            "strategies",
            {
                "name": name,
                "version": version,
                "description": payload.get("description") or "",
                "param_schema": json.dumps(params_schema, ensure_ascii=False),
                "file_path": file_path,
                "interface_type": _interface_label(validation),
                "status": payload.get("status") or "草稿",
                "origin": origin,
                "tags": json.dumps(payload.get("tags") or [], ensure_ascii=False),
                "created_at": now,
                "updated_at": now,
            },
        )
        return self.get(row["id"], include_code=True)

    def update(self, strategy_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.repo.get("strategies", strategy_id)
        values: dict[str, Any] = {"updated_at": utc_now_iso()}
        if payload.get("name") is not None:
            values["name"] = payload["name"]
        if payload.get("description") is not None:
            values["description"] = payload["description"]
        if payload.get("default_params") is not None:
            values["param_schema"] = json.dumps(payload["default_params"], ensure_ascii=False)
        if payload.get("tags") is not None:
            values["tags"] = json.dumps(payload["tags"], ensure_ascii=False)
        if payload.get("code") is not None:
            validation = self.validator.validate_source(payload["code"])
            values["interface_type"] = _interface_label(validation)
            self.storage.write_text(current["file_path"], payload["code"])
        self.repo.update("strategies", strategy_id, values)
        return self.get(strategy_id, include_code=True)

    def set_status(self, strategy_id: int, status: str) -> dict[str, Any]:
        self.repo.update("strategies", strategy_id, {"status": status, "updated_at": utc_now_iso()})
        return self.get(strategy_id, include_code=False)

    def delete(self, strategy_id: int) -> None:
        row = self.repo.get("strategies", strategy_id)
        self.repo.delete("strategies", strategy_id)
        self.storage.delete(row["file_path"])

    def params(self, strategy_id: int) -> Any:
        row = self.repo.get("strategies", strategy_id)
        return json_loads(row.get("param_schema"), {})

    def interface_report(
        self,
        strategy_id: int,
        params: dict[str, Any] | None = None,
        symbols: StrategySymbols | None = None,
    ) -> dict[str, Any]:
        row = self.repo.get("strategies", strategy_id)
        strategy_params = _runtime_params(params if params is not None else json_loads(row.get("param_schema"), {}))
        try:
            code = self.storage.read_text(row["file_path"])
            validation = self.validator.validate_source(code)
            report = StrategyLoader(self.storage).dry_run(row["file_path"], params=strategy_params, symbols=symbols)
            report["validation"] = validation
            return report
        except Exception as exc:
            return {
                "valid": False,
                "file_path": row.get("file_path"),
                "error": str(exc),
            }

    def examples(self) -> StrategyExampleRows:
        if not EXAMPLE_STRATEGY_DIR.exists():
            return []
        items: StrategyExampleRows = []
        for path in sorted(EXAMPLE_STRATEGY_DIR.glob("*.py")):
            relative_path = path.relative_to(PROJECT_ROOT).as_posix()
            item = {"name": path.stem, "path": relative_path, "valid": True}
            try:
                validation = self.validator.validate_source(path.read_text(encoding="utf-8"))
                item.update(
                    {
                        "adapter_type": validation.get("adapter_type"),
                        "entry": validation.get("entry_class") or validation.get("entry_func"),
                        "capabilities": validation.get("capabilities") or [],
                    }
                )
            except Exception as exc:
                item.update({"valid": False, "error": str(exc)})
            items.append(item)
        return items

    def example_detail(self, relative_path: str) -> dict[str, Any]:
        target = _resolve_example_path(relative_path)
        code = target.read_text(encoding="utf-8")
        validation = self.validator.validate_source(code)
        return {
            "name": target.stem,
            "path": target.relative_to(PROJECT_ROOT).as_posix(),
            "code": code,
            "validation": validation,
            "intro": _load_example_intros().get(target.name, {}),
        }

    def import_example(self, relative_path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        detail = self.example_detail(relative_path)
        values = dict(payload or {})
        validation = detail["validation"]
        intro = detail.get("intro") or {}
        values["name"] = (
            values.get("name")
            or intro.get("title")
            or (validation.get("entry_class") or validation.get("entry_func") or detail["name"])
        )
        values["version"] = values.get("version") or "v1"
        values["description"] = values.get("description") or intro.get("title") or "egs 示例策略"
        values["code"] = detail["code"]
        values["default_params"] = (
            values.get("default_params") or intro.get("default_params") or _params_defaults(validation)
        )
        values["tags"] = values.get("tags") or intro.get("tags") or ["egs", "标准端口"]
        return self.create(values, origin="egs 示例")


def _interface_label(validation: dict[str, Any]) -> str:
    adapter_type = str(validation.get("adapter_type") or "class_port")
    entry = validation.get("entry_class") or validation.get("entry_func") or "-"
    label = INTERFACE_LABELS.get(adapter_type, adapter_type)
    return f"{label} / {entry}"


def _runtime_params(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        params: dict[str, Any] = {}
        for item in value:
            if isinstance(item, dict) and item.get("name"):
                params[str(item["name"])] = item.get("default")
        return params
    return {}


def _params_defaults(validation: dict[str, Any]) -> dict[str, Any]:
    schema = validation.get("params_schema")
    if isinstance(schema, dict):
        return dict(schema)
    if isinstance(schema, list):
        return {
            str(item["name"]): item.get("default") for item in schema if isinstance(item, dict) and item.get("name")
        }
    return {}


def _load_example_intros() -> dict[str, dict[str, Any]]:
    if not EXAMPLE_INTRO_FILE.exists():
        return {}
    try:
        loaded = yaml.safe_load(EXAMPLE_INTRO_FILE.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        get_logger("strategy").warning(f"预制策略介绍配置解析失败: {exc}")
        return {}
    strategies = loaded.get("strategies") if isinstance(loaded, dict) else None
    return strategies if isinstance(strategies, dict) else {}


def _resolve_example_path(relative_path: str) -> Path:
    target = (PROJECT_ROOT / str(relative_path)).resolve()
    base = EXAMPLE_STRATEGY_DIR.resolve()
    if target != base and not str(target).startswith(str(base) + "\\") and not str(target).startswith(str(base) + "/"):
        raise BusinessError(ErrorCode.STORAGE_ERROR, "示例策略路径越界")
    if not target.exists() or target.suffix != ".py":
        raise BusinessError(ErrorCode.NOT_FOUND, "示例策略不存在")
    return target
