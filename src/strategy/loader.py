"""Load strategy files and expose them through the standard strategy port."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.file_storage import FileStorage

from .adapters import BAR_METHODS, TICK_METHODS, FunctionStrategyAdapter, ObjectStrategyAdapter
from .execution_policy import execution_config, execution_kind
from .ports import MarketEvent, StrategyContext, StrategyPort
from .process_port import ProcessStrategyPort
from .strategy_base import StrategyBase

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class LoadedStrategy:
    adapter: StrategyPort
    file_path: Path
    metadata: dict[str, Any]


class StrategyLoader:
    """Runtime loader for uploaded, CLI-generated and egs strategies."""

    def __init__(self, storage: FileStorage | None = None) -> None:
        self.storage = storage or FileStorage()

    def load_from_file(
        self,
        file_path: str | Path,
        params: dict[str, Any] | None = None,
        entry: str | None = None,
    ) -> LoadedStrategy:
        target = self._resolve_path(file_path)
        source = target.read_bytes()
        kind = execution_kind(target, source)
        if kind == "reviewed_worker":
            adapter = ProcessStrategyPort(target, params or {}, entry, source=source)
            return LoadedStrategy(
                adapter,
                target,
                {
                    "adapter_type": adapter.adapter_type,
                    "entry_name": adapter.entry_name,
                    "capabilities": adapter.capabilities,
                    "params_schema": adapter.params_schema,
                    "file_path": target.as_posix(),
                    "execution": kind,
                },
            )
        return self._load_local(target, params or {}, entry, source=source)

    def _load_local(self, target: Path, params: dict[str, Any], entry: str | None, *, source: bytes | None = None):
        module = self._load_module(target, source=source)
        adapter = self._build_adapter(module, params, entry)
        metadata = {
            "adapter_type": adapter.adapter_type,
            "entry_name": adapter.entry_name,
            "capabilities": adapter.capabilities,
            "params_schema": adapter.params_schema,
            "file_path": target.as_posix(),
        }
        return LoadedStrategy(adapter=adapter, file_path=target, metadata=metadata)

    def dry_run(
        self,
        file_path: str | Path,
        params: dict[str, Any] | None = None,
        symbols: list[str] | None = None,
        entry: str | None = None,
    ) -> dict[str, Any]:
        loaded = self.load_from_file(file_path, params=params, entry=entry)
        sample = execution_config()["dry_run"]
        run_symbols = symbols or [sample["symbol"]]
        context = StrategyContext(
            params=params or {},
            symbols=run_symbols,
            mode="dry_run",
            metadata={"source": loaded.file_path.as_posix()},
        )
        event = MarketEvent(
            symbol=run_symbols[0],
            timestamp=sample["timestamp"],
            open=sample["open"],
            high=sample["high"],
            low=sample["low"],
            close=sample["close"],
            volume=sample["volume"],
        )
        loaded.adapter.on_start(context)
        if "bar" in loaded.adapter.capabilities:
            signals = loaded.adapter.on_bar(event, context)
            event_type = "bar"
        else:
            signals = loaded.adapter.on_tick(event, context)
            event_type = "tick"
        loaded.adapter.on_stop(context)
        report = dict(loaded.metadata)
        report.update(
            {
                "valid": True,
                "event_type": event_type,
                "signal_count": len(signals),
                "sample_signals": [signal.to_dict() for signal in signals[:5]],
            }
        )
        return report

    def _resolve_path(self, file_path: str | Path) -> Path:
        candidate = Path(file_path)
        if candidate.is_absolute():
            target = candidate.resolve()
            if not target.is_relative_to(PROJECT_ROOT):
                raise BusinessError(ErrorCode.STORAGE_ERROR, "策略文件必须位于本项目中")
            return target
        if str(file_path).replace("\\", "/").startswith("strategies/"):
            return self.storage.resolve(str(file_path))
        target = (PROJECT_ROOT / candidate).resolve()
        if not target.is_relative_to(PROJECT_ROOT):
            raise BusinessError(ErrorCode.STORAGE_ERROR, "策略文件必须位于本项目中")
        return target

    def _load_module(self, file_path: Path, *, source: bytes | None = None) -> ModuleType:
        if not file_path.exists():
            raise BusinessError(ErrorCode.NOT_FOUND, "策略文件不存在")
        digest = hashlib.sha1(file_path.as_posix().encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
        module_name = f"_loaded_strategy_{digest}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise BusinessError(ErrorCode.STRATEGY_INVALID, "策略文件无法加载")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            frozen = file_path.read_bytes() if source is None else source
            exec(compile(frozen, str(file_path), "exec"), module.__dict__)
        finally:
            sys.modules.pop(module_name, None)
        return module

    def _build_adapter(self, module: ModuleType, params: dict[str, Any], entry: str | None) -> StrategyPort:
        if entry:
            target = getattr(module, entry, None)
            if target is None:
                raise BusinessError(ErrorCode.STRATEGY_INVALID, "指定策略入口不存在")
            return self._adapter_for_entry(target, params, entry)

        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__ or cls is StrategyBase:
                continue
            if issubclass(cls, StrategyBase):
                return ObjectStrategyAdapter(_instantiate(cls, params), "strategy_base_class", cls.__name__)
            if _class_has_methods(cls, BAR_METHODS + TICK_METHODS):
                return ObjectStrategyAdapter(_instantiate(cls, params), "class_port", cls.__name__)

        for name, callback in inspect.getmembers(module, inspect.isfunction):
            if callback.__module__ == module.__name__ and name in BAR_METHODS + TICK_METHODS:
                capability = "tick" if name in TICK_METHODS else "bar"
                return FunctionStrategyAdapter(callback, "function_port", name, capability)

        raise BusinessError(ErrorCode.STRATEGY_INVALID, "策略文件未找到可加载入口")

    def _adapter_for_entry(self, target: Any, params: dict[str, Any], entry: str) -> StrategyPort:
        if inspect.isclass(target):
            adapter_type = "strategy_base_class" if issubclass(target, StrategyBase) else "class_port"
            return ObjectStrategyAdapter(_instantiate(target, params), adapter_type, entry)
        if inspect.isfunction(target):
            capability = "tick" if entry in TICK_METHODS else "bar"
            return FunctionStrategyAdapter(target, "function_port", entry, capability)
        if _class_has_methods(target.__class__, BAR_METHODS + TICK_METHODS):
            return ObjectStrategyAdapter(target, "object_port", entry)
        raise BusinessError(ErrorCode.STRATEGY_INVALID, "指定策略入口不符合标准端口")


def _class_has_methods(cls: type[Any], names: tuple[str, ...]) -> bool:
    return any(callable(getattr(cls, name, None)) for name in names)


def _instantiate(cls: type[Any], params: dict[str, Any]) -> Any:
    last_error: TypeError | None = None
    for args, kwargs in (((params,), {}), ((), {"params": params}), ((), {})):
        try:
            return cls(*args, **kwargs)
        except TypeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return cls()
