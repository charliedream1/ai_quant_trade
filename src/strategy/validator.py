"""Strategy source validation."""

from __future__ import annotations

import ast
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode

BAR_METHODS = {"on_bar", "handle_bar", "generate_signal", "generate_signals"}
TICK_METHODS = {"on_tick", "handle_tick"}
START_METHODS = {"on_start", "on_init", "initialize", "init"}
STOP_METHODS = {"on_stop", "finish", "teardown"}
RISK_METHODS = {"on_risk_check", "risk_check"}
FUNCTION_ENTRIES = BAR_METHODS | TICK_METHODS


class StrategyValidator:
    DANGEROUS_NAMES = {"eval", "exec", "compile", "__import__", "open", "input"}
    DANGEROUS_MODULES = {"os", "subprocess", "socket", "shutil", "ctypes", "pathlib"}

    def validate_source(self, code: str) -> dict[str, Any]:
        if not code or not code.strip():
            raise BusinessError(ErrorCode.STRATEGY_INVALID, "策略代码不能为空")
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise BusinessError(ErrorCode.STRATEGY_INVALID, f"策略代码语法错误: {exc}") from exc

        self._check_safety(tree)
        classes: list[str] = []
        class_entries: list[dict[str, Any]] = []
        function_entries: list[str] = []
        module_params_schema = self._module_params_schema(tree)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
                method_names = {body.name for body in node.body if isinstance(body, ast.FunctionDef)}
                base_names = {_base_name(base) for base in node.bases}
                is_strategy_base = "StrategyBase" in base_names
                signal_methods = sorted(method_names & (BAR_METHODS | TICK_METHODS))
                if signal_methods or is_strategy_base:
                    class_entries.append(
                        {
                            "name": node.name,
                            "adapter_type": "strategy_base_class" if is_strategy_base else "class_port",
                            "methods": sorted(method_names),
                            "capabilities": _capabilities(method_names),
                            "params_schema": self._class_params_schema(node),
                        }
                    )
            elif isinstance(node, ast.FunctionDef) and node.name in FUNCTION_ENTRIES:
                function_entries.append(node.name)

        if not class_entries and not function_entries:
            raise BusinessError(
                ErrorCode.STRATEGY_INVALID,
                "策略必须实现标准策略端口：类 on_bar/on_tick/handle_bar/generate_signal，或同名函数入口",
            )

        entry_class = class_entries[0]["name"] if class_entries else None
        entry_func = function_entries[0] if function_entries else None
        params_schema = class_entries[0].get("params_schema") if class_entries else module_params_schema
        if params_schema in (None, []):
            params_schema = module_params_schema
        adapter_type = class_entries[0]["adapter_type"] if class_entries else "function_port"
        capabilities = class_entries[0]["capabilities"] if class_entries else _capabilities({entry_func or ""})
        return {
            "valid": True,
            "classes": classes,
            "functions": function_entries,
            "entry_class": entry_class,
            "entry_func": entry_func,
            "adapter_type": adapter_type,
            "capabilities": capabilities,
            "params_schema": params_schema or {},
        }

    def _check_safety(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name.split(".")[0] for alias in node.names]
                elif node.module:
                    modules = [node.module.split(".")[0]]
                if any(module in self.DANGEROUS_MODULES for module in modules):
                    raise BusinessError(ErrorCode.STRATEGY_INVALID, "策略代码包含危险模块导入")
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in self.DANGEROUS_NAMES:
                    raise BusinessError(ErrorCode.STRATEGY_INVALID, f"策略代码包含危险调用: {func.id}")

    def _module_params_schema(self, tree: ast.Module) -> Any:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"params_schema", "PARAMS_SCHEMA"}:
                        return _literal_or_empty(node.value)
        return {}

    def _class_params_schema(self, node: ast.ClassDef) -> Any:
        for body in node.body:
            if isinstance(body, ast.Assign):
                for target in body.targets:
                    if isinstance(target, ast.Name) and target.id == "params_schema":
                        return _literal_or_empty(body.value)
        return {}


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def _literal_or_empty(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return {}


def _capabilities(method_names: set[str]) -> list[str]:
    capabilities: list[str] = []
    for label, candidates in (
        ("start", START_METHODS),
        ("bar", BAR_METHODS),
        ("tick", TICK_METHODS),
        ("risk_check", RISK_METHODS),
        ("stop", STOP_METHODS),
    ):
        if method_names & candidates:
            capabilities.append(label)
    if not capabilities and method_names & FUNCTION_ENTRIES:
        capabilities.append("bar")
    return capabilities
