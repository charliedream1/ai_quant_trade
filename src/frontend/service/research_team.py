"""Progressive UI callbacks for multi-agent backtest review."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yaml

from src.agent.providers.contracts import ModelSelection
from src.agent.research_team import ResearchTeam
from src.core.repository import Repository

from .foundation import require_id, require_text, ui_error_message

TEAM_COLUMNS = ["角色", "结论", "模型", "工具调用", "耗时(ms)", "证据", "摘要"]
VERDICT_LABELS = {"approve": "可继续研究", "watch": "需补充验证", "reject": "不通过"}
STATUS_LABELS = {"running": "运行中", "finished": "已完成", "failed": "失败"}


class ResearchTeamServiceMixin:
    def research_team_model_choices(self) -> list[tuple[str, int]]:
        rows = Repository().db.query("SELECT id, name FROM llm_models WHERE enabled = 1 ORDER BY is_default DESC, id")
        return [("系统默认", 0), *((str(row["name"]), int(row["id"])) for row in rows)]

    def research_team_review(
        self,
        backtest_id: Any,
        objective: str,
        model_id: Any,
        workflow: str = "backtest_review",
        backend="api",
        model_name="",
        reasoning_effort="",
        role_models="{}",
    ):
        try:
            task_id = require_id(backtest_id, "回测 ID")
            selected_model = int(model_id) if model_id and int(model_id) > 0 else None
            provider = ModelSelection(
                backend=backend,
                model_id=selected_model if backend == "api" else None,
                model_name=model_name,
                reasoning_effort=reasoning_effort,
            ).model_dump(exclude_none=True)
            overrides = yaml.safe_load(role_models or "{}")
            if not isinstance(overrides, dict):
                raise ValueError("角色配置必须为YAML对象")
            overrides = {
                role: ModelSelection.model_validate(value).model_dump(exclude_unset=True, exclude_none=True)
                for role, value in overrides.items()
            }
            stream = ResearchTeam().run_stream(
                task_id,
                require_text(objective, "研究目标"),
                selected_model,
                workflow or "backtest_review",
                provider,
                overrides,
            )
            for report in stream:
                yield _render_report(report)
        except Exception as exc:
            yield f"多 Agent 复核未完成：{ui_error_message(exc)}", pd.DataFrame(columns=TEAM_COLUMNS), ""


def _render_report(report: dict[str, Any]) -> tuple[str, pd.DataFrame, str]:
    roles = list((report.get("roles") or {}).values())
    rows = [
        {
            "角色": role["name"],
            "结论": VERDICT_LABELS.get(role["verdict"], role["verdict"]),
            "模型": role["model"],
            "工具调用": len(role["tool_events"]),
            "耗时(ms)": role["duration_ms"],
            "证据": ", ".join(role["evidence_ids"]),
            "摘要": role["summary"],
        }
        for role in roles
    ]
    pending = [event["role"] for event in report.get("events") or [] if event.get("status") == "running"]
    active = pending[-1] if pending and report["status"] == "running" else "-"
    workflow_label = "ETF策略复核" if report.get("workflow") == "etf_review" else "回测复核"
    status = f"工作流：{workflow_label} · 状态：{STATUS_LABELS.get(report['status'], report['status'])} · 已完成 {len(roles)}/4 · 当前角色：{active} · 运行：{report['run_id']}"
    details = [
        f"### 多 Agent 研究复核\n\n- 回测：{report['backtest_id']}\n- 最终结论：{VERDICT_LABELS.get(str(report.get('verdict') or ''), '处理中')}"
    ]
    for flag in report.get("hard_flags") or []:
        details.append(f"- 系统检查：{flag}")
    for role in roles:
        details.append(f"\n**{role['name']}**\n\n{role['summary']}")
        details.extend(f"- {concern}" for concern in role["concerns"])
    if report.get("error"):
        details.append(f"\n失败原因：{report['error']}")
    details.append("\n研究报告仅用于复核；不执行交易。")
    return status, pd.DataFrame(rows, columns=TEAM_COLUMNS), "\n\n".join(details)
