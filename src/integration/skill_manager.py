"""Skill registry, parameter validation, and built-in runners."""

from __future__ import annotations

import json
from typing import Any

from src.core.exceptions import BusinessError, ErrorCode
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.engine.insights.config import insight_config
from src.engine.insights.service import InsightReportService
from src.engine.market import NewsAggregator

DEFAULT_SKILLS = (
    {
        "name": "news_summary",
        "description": "财经新闻摘要",
        "source": "内置",
        "param_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                "refresh": {"type": "boolean"},
            },
        },
    },
    {
        "name": "strategy_review",
        "description": "策略代码审查",
        "source": "内置",
        "param_schema": {
            "type": "object",
            "properties": {"strategy_id": {"type": "integer", "required": True}},
        },
    },
)


class SkillManager:
    def __init__(self, repo: Repository | None = None) -> None:
        self.repo = repo or Repository()

    def seed_defaults(self) -> None:
        now = utc_now_iso()
        config = insight_config()
        insight_defaults = tuple(
            {
                "name": name,
                "description": task["label"],
                "source": config["registry"]["source"],
                "param_schema": config["registry"]["param_schema"],
            }
            for name, task in config["tasks"].items()
        )
        for default in (*DEFAULT_SKILLS, *insight_defaults):
            row = self.repo.db.query_one("SELECT * FROM skills WHERE name = ?", (default["name"],))
            if row is None:
                self.repo.insert(
                    "skills",
                    {
                        **default,
                        "param_schema": json.dumps(default["param_schema"], ensure_ascii=False),
                        "params": "{}",
                        "enabled": 0,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                continue
            if not json_loads(row.get("param_schema"), {}):
                self.repo.update(
                    "skills",
                    int(row["id"]),
                    {
                        "description": default["description"],
                        "source": default["source"],
                        "param_schema": json.dumps(default["param_schema"], ensure_ascii=False),
                        "updated_at": now,
                    },
                )

    def list(self) -> list[dict[str, Any]]:
        self.seed_defaults()
        rows = self.repo.list("skills", order_by="id ASC")
        for row in rows:
            self._shape(row)
        return rows

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Register a Skill contract without importing or executing uploaded code."""
        name = str(payload.get("name") or "").strip()
        description = str(payload.get("description") or "").strip()
        source = str(payload.get("source") or "用户登记").strip()
        if not name:
            raise BusinessError(ErrorCode.MISSING_PARAM, "Skill 名称不能为空。")
        if len(name) > 120:
            raise BusinessError(ErrorCode.INVALID_PARAM, "Skill 名称不能超过 120 个字符。")
        schema = payload.get("param_schema") or {}
        params = payload.get("params") or {}
        if not isinstance(schema, dict) or not isinstance(params, dict):
            raise BusinessError(ErrorCode.INVALID_PARAM, "Skill schema 和默认参数必须是 JSON 对象。")
        self.seed_defaults()
        if self.repo.db.query_one("SELECT id FROM skills WHERE name = ?", (name,)):
            raise BusinessError(ErrorCode.CONSTRAINT_CONFLICT, f"Skill {name} 已存在。")
        now = utc_now_iso()
        row = self.repo.insert(
            "skills",
            {
                "name": name,
                "description": description,
                "source": source,
                "param_schema": json.dumps(schema, ensure_ascii=False),
                "params": json.dumps(params, ensure_ascii=False),
                "enabled": 0,
                "created_at": now,
                "updated_at": now,
            },
        )
        return self._shape(row)

    def enable(self, skill_id: int, enabled: bool) -> dict[str, Any]:
        return self._shape(
            self.repo.update("skills", skill_id, {"enabled": 1 if enabled else 0, "updated_at": utc_now_iso()})
        )

    def params(self, skill_id: int, params: dict[str, Any]) -> dict[str, Any]:
        row = self.repo.get("skills", skill_id)
        schema = json_loads(row.get("param_schema"), {})
        _validate_params(params, schema)
        return self._shape(
            self.repo.update(
                "skills",
                skill_id,
                {"params": json.dumps(params or {}, ensure_ascii=False), "updated_at": utc_now_iso()},
            )
        )

    def run(self, skill_id: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
        row = self.repo.get("skills", skill_id)
        shaped = self._shape(row)
        if not shaped["enabled"]:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"Skill {shaped['name']} 尚未启用。")
        payload = params or shaped["params"]
        _validate_params(payload, shaped["param_schema"])
        name = str(shaped["name"])
        if name in insight_config()["tasks"]:
            return InsightReportService().start({**payload, "kind": name})
        if name == "news_summary":
            return _run_news_summary(payload)
        if name == "strategy_review":
            return {
                "skill_id": skill_id,
                "name": name,
                "status": "blocked",
                "message": "策略代码审查执行器尚未接入，当前仅完成参数校验。",
                "params": payload,
            }
        raise BusinessError(ErrorCode.CONFIG_DEPENDENCY, f"Skill {name} 没有可用的本地执行器。")

    @staticmethod
    def _shape(row: dict[str, Any]) -> dict[str, Any]:
        row["skill_id"] = row["id"]
        row["enabled"] = bool(row.get("enabled"))
        row["param_schema"] = json_loads(row.get("param_schema"), {})
        row["params"] = json_loads(row.get("params"), {})
        return row


def _validate_params(params: dict[str, Any], schema: Any) -> None:
    if not isinstance(params, dict):
        raise BusinessError(ErrorCode.INVALID_PARAM, "Skill 参数必须是 JSON 对象。")
    if not isinstance(schema, dict):
        return
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return
    missing = [
        name
        for name, definition in properties.items()
        if isinstance(definition, dict) and definition.get("required") and name not in params
    ]
    if missing:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"Skill 缺少必填参数：{', '.join(missing)}")
    for name, value in params.items():
        definition = properties.get(name)
        if not isinstance(definition, dict):
            continue
        _validate_param_type(name, value, definition)


def _validate_param_type(name: str, value: Any, definition: dict[str, Any]) -> None:
    expected = str(definition.get("type") or "")
    valid = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }.get(expected, True)
    if not valid:
        raise BusinessError(ErrorCode.INVALID_PARAM, f"Skill 参数 {name} 类型应为 {expected}。")
    if isinstance(value, int | float) and not isinstance(value, bool):
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        if isinstance(minimum, int | float) and value < minimum:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"Skill 参数 {name} 小于最小值。")
        if isinstance(maximum, int | float) and value > maximum:
            raise BusinessError(ErrorCode.INVALID_PARAM, f"Skill 参数 {name} 超过最大值。")


def _run_news_summary(params: dict[str, Any]) -> dict[str, Any]:
    limit = int(params.get("limit") or 10)
    result = NewsAggregator().list_news(
        category=None,
        keyword=str(params.get("keyword") or "").strip() or None,
        source=None,
        page=1,
        page_size=limit,
        refresh=bool(params.get("refresh", False)),
    )
    return {
        "skill_id": None,
        "name": "news_summary",
        "status": "success",
        "total": int(result.get("total") or 0),
        "items": result.get("items") or [],
    }
