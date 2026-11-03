"""Custom scheduled job executor registry."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.core.config import get_settings
from src.core.logger import get_logger

ExecutorCallable = Callable[..., Any]
SUCCESS_STATUS = "成功"


@dataclass(frozen=True)
class ExecutorSpec:
    key: str
    target: str
    description: str = ""


class CustomExecutorRegistry:
    """Load and run configured custom scheduled job executors."""

    def __init__(self) -> None:
        self.log = get_logger("scheduler.registry")
        self.settings = get_settings()

    def execute(self, key: str, params: dict[str, Any], job: dict[str, Any]) -> dict[str, Any] | None:
        spec = self._specs().get(key)
        if spec is None:
            return None
        handler = self._load_handler(spec)
        result = self._call_handler(handler, params, job)
        return self._normalize_result(result, spec)

    def _specs(self) -> dict[str, ExecutorSpec]:
        config_path = self._config_path()
        if config_path is None:
            return {}
        if not config_path.exists():
            self.log.warning("custom scheduler executor config not found | path={}", config_path)
            return {}
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            self.log.warning(
                "custom scheduler executor config ignored because root is not a mapping | path={}", config_path
            )
            return {}
        entries = raw.get("executors", {})
        if not isinstance(entries, dict):
            self.log.warning(
                "custom scheduler executor config ignored because executors is not a mapping | path={}", config_path
            )
            return {}
        specs: dict[str, ExecutorSpec] = {}
        for key, entry in entries.items():
            spec = self._parse_spec(str(key).strip(), entry, config_path.parent)
            if spec is not None:
                specs[spec.key] = spec
        return specs

    def _config_path(self) -> Path | None:
        path = self.settings.scheduler_executors_path
        if path is None:
            return None
        return path if path.is_absolute() else (self.settings.project_root / path).resolve()

    def _parse_spec(self, key: str, entry: Any, base_dir: Path) -> ExecutorSpec | None:
        if not key:
            return None
        description = ""
        if isinstance(entry, str):
            target = entry.strip()
        elif isinstance(entry, dict):
            target = _entry_target(entry, base_dir)
            description = str(entry.get("description") or "").strip()
        else:
            self.log.warning("custom scheduler executor ignored because entry is invalid | key={}", key)
            return None
        if not target:
            self.log.warning("custom scheduler executor ignored because target is empty | key={}", key)
            return None
        return ExecutorSpec(key=key, target=target, description=description)

    def _load_handler(self, spec: ExecutorSpec) -> ExecutorCallable:
        module_target, function_name = _split_target(spec.target)
        if module_target.endswith(".py") or "/" in module_target or "\\" in module_target:
            module = self._load_file_module(module_target, spec.key)
        else:
            module = importlib.import_module(module_target)
        handler = getattr(module, function_name)
        if not callable(handler):
            raise TypeError(f"自定义执行体 {spec.key} 的目标 {spec.target} 不可调用")
        return handler

    def _load_file_module(self, module_target: str, key: str) -> object:
        module_path = Path(module_target)
        if not module_path.is_absolute():
            module_path = self.settings.project_root / module_path
        module_path = module_path.resolve()
        _ensure_inside_project(module_path, self.settings.project_root.resolve())
        if not module_path.exists():
            raise FileNotFoundError(f"自定义执行体文件不存在: {module_path}")
        module_name = f"_scheduler_custom_{key}_{abs(hash(module_path))}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载自定义执行体文件: {module_path}")
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        return module

    @staticmethod
    def _call_handler(handler: ExecutorCallable, params: dict[str, Any], job: dict[str, Any]) -> Any:
        signature = inspect.signature(handler)
        positional = [
            item
            for item in signature.parameters.values()
            if item.kind in {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
        ]
        if any(item.kind == inspect.Parameter.VAR_KEYWORD for item in signature.parameters.values()):
            return handler(params=params, job=job)
        if not positional:
            return handler()
        if len(positional) == 1:
            return handler(params)
        return handler(params, job)

    @staticmethod
    def _normalize_result(result: Any, spec: ExecutorSpec) -> dict[str, Any]:
        if isinstance(result, dict):
            payload = dict(result)
        elif result is None:
            payload = {}
        else:
            payload = {"summary": str(result)}
        payload.setdefault("status", SUCCESS_STATUS)
        payload.setdefault("summary", f"自定义执行体 {spec.key} 执行完成。")
        details = payload.get("details")
        payload["details"] = details if isinstance(details, dict) else {}
        payload["details"].setdefault("executor_key", spec.key)
        if spec.description:
            payload["details"].setdefault("executor_description", spec.description)
        return payload


def _entry_target(entry: dict[str, Any], base_dir: Path) -> str:
    raw_target = str(entry.get("target") or "").strip()
    if raw_target:
        return raw_target
    function_name = str(entry.get("callable") or entry.get("function") or "").strip()
    module_name = str(entry.get("module") or "").strip()
    path_value = str(entry.get("path") or "").strip()
    if path_value:
        path = Path(path_value)
        path = path if path.is_absolute() else (base_dir / path).resolve()
        return f"{path}:{function_name}"
    if module_name:
        return f"{module_name}:{function_name}"
    return ""


def _split_target(target: str) -> tuple[str, str]:
    if ":" not in target:
        raise ValueError("自定义执行体 target 必须使用 module_or_path:function 格式")
    module_target, function_name = [item.strip() for item in target.rsplit(":", 1)]
    if not module_target or not function_name:
        raise ValueError("自定义执行体 target 的模块/路径和函数名不能为空")
    return module_target, function_name


def _ensure_inside_project(path: Path, project_root: Path) -> None:
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"自定义执行体文件必须位于项目目录内: {path}") from exc
