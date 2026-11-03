"""Read project-local YAML parameter schemes without importing strategy code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from src.core.exceptions import BusinessError, ErrorCode

PROFILE_ROOT = Path(__file__).resolve().parents[2] / "egs" / "strategy_params"
RESERVED_KEYS = {"_backtest", "_experiment"}


def parameter_mapping(value: Any, label: str) -> dict[str, Any]:
    """Require finite JSON-compatible parameters; reserve platform metadata keys."""
    if value is None:
        return {}
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BusinessError(ErrorCode.INVALID_PARAM, f"{label}必须是键值对对象")
    if RESERVED_KEYS.intersection(value):
        raise BusinessError(ErrorCode.INVALID_PARAM, f"{label}不能包含平台保留字段 _backtest / _experiment")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        result: dict[str, Any] = json.loads(encoded)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"{label}必须使用有限数值和 JSON 兼容类型") from exc
    return result


class ParameterProfiles:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or PROFILE_ROOT).resolve()

    def family(self, entry: str) -> dict[str, Any]:
        matches = []
        for path in sorted(self.root.glob("*.yaml")):
            target = path.resolve()
            if target.parent != self.root:
                raise BusinessError(ErrorCode.INVALID_PARAM, "参数方案文件不能指向方案目录外")
            raw = target.read_bytes()
            try:
                payload = yaml.safe_load(raw.decode("utf-8-sig"))
            except (UnicodeError, yaml.YAMLError) as exc:
                raise BusinessError(ErrorCode.INVALID_PARAM, f"参数方案文件格式错误：{path.name}") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("entry"), str):
                raise BusinessError(ErrorCode.INVALID_PARAM, f"参数方案缺少策略入口：{path.name}")
            if payload["entry"] == entry:
                matches.append({**payload, "file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
        if len(matches) > 1:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"策略入口 {entry} 对应多个参数方案文件，请合并配置")
        return matches[0] if matches else {}

    def options(self, family: dict[str, Any]) -> list[dict[str, Any]]:
        profiles = family.get("profiles", {})
        if not isinstance(profiles, dict):
            raise BusinessError(ErrorCode.INVALID_PARAM, "参数方案 profiles 必须是键值对对象")
        options = []
        for key, value in profiles.items():
            if not isinstance(key, str) or not key or ":" in key or not isinstance(value, dict):
                raise BusinessError(ErrorCode.INVALID_PARAM, "参数方案名称或内容不合法")
            options.append(
                {
                    "id": f"{family['file']}:{key}",
                    "label": str(value.get("label") or key),
                    "description": str(value.get("description") or ""),
                    "params": parameter_mapping(value.get("params", {}), "方案参数"),
                }
            )
        return options

    def select(self, family: dict[str, Any], profile_id: str | None) -> dict[str, Any]:
        if not profile_id:
            return {}
        for option in self.options(family):
            if option["id"] == profile_id:
                return option
        raise BusinessError(ErrorCode.INVALID_PARAM, "参数方案不存在或不属于当前策略，请重新选择")
