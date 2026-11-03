"""Ai frontend service callbacks."""

from __future__ import annotations

from itertools import chain
from typing import cast

import gradio as gr
from src.agent.composer_config import normalize_backend
from src.agent.workspace import AIWorkspaceService
from src.core.config import get_settings
from src.core.exceptions import BusinessError
from src.documents.access import project_file
from src.documents.config import preview_config

from .contracts import CrossDomainCallbacks
from .foundation import (
    ACCOUNT_MODE_CHOICES,
    AI_CONSOLE_GENERIC_BACKEND,
    AI_EXPERT_CHOICES,
    AI_EXPERT_COLUMNS,
    AI_EXPERT_GROUP_CHOICES,
    AI_JOB_TEMPLATE_COLUMNS,
    AI_PROJECT_FILE_COLUMNS,
    AI_PROJECT_IGNORED_NAMES,
    AI_PROJECT_TEXT_SUFFIXES,
    AI_PROJECT_TREE_LIMIT,
    AI_TASK_TYPE_CHOICES,
    AI_TEAM_COLUMNS,
    AI_WORKSPACE_NAV_COLUMNS,
    AI_WORKSPACE_SESSION_COLUMNS,
    CLI_PROVIDERS,
    PROJECT_ROOT,
    QUANT_WORKFLOW_ADVICE_COLUMNS,
    QUANT_WORKFLOW_ARTIFACT_COLUMNS,
    QUANT_WORKFLOW_INSIGHT_COLUMNS,
    QUANT_WORKFLOW_MODE_CHOICES,
    QUANT_WORKFLOW_QUESTION_COLUMNS,
    QUANT_WORKFLOW_RUN_COLUMNS,
    QUANT_WORKFLOW_STEP_COLUMNS,
    Any,
    LLMClient,
    Path,
    QuantWorkflowService,
    Repository,
    Sequence,
    _chat_history_messages,
    _choice_label,
    _normalize_account_mode,
    _normalize_ai_task_type,
    _optional_id,
    _ordered_steps,
    _preset_by_id,
    _preset_items,
    _workflow_items,
    ai_console_model_choices,
    compact_json,
    escape,
    pd,
    require_id,
    require_text,
    to_frame,
)
from .insights import InsightsServiceMixin
from .research_team import ResearchTeamServiceMixin
from .visuals import (
    _format_display_time,
)


class AIServiceMixin(ResearchTeamServiceMixin, InsightsServiceMixin):
    """Callbacks owned by the ai frontend domain."""

    def ai_console_model_choices(self) -> list[tuple[str, str]]:
        return ai_console_model_choices()

    def quant_workflow_sop_cards(self) -> str:
        cards = []
        mode_labels = {value: label for label, value in QUANT_WORKFLOW_MODE_CHOICES}
        for item in _workflow_items("sops"):
            stages = item.get("stages") or []
            stage_tags = "".join(
                "<span>" + escape(str(stage.get("title") or stage.get("key") or "-")) + "</span>"
                for stage in stages[:5]
                if isinstance(stage, dict)
            )
            mode = str(item.get("mode") or "")
            cards.append(
                "<article class='quant-flow-card'><small>"
                + escape(mode_labels.get(mode, mode or "-"))
                + "</small><h3>"
                + escape(str(item.get("name") or "-"))
                + "</h3><p>"
                + escape(str(item.get("description") or "-"))
                + "</p><div>"
                + stage_tags
                + "</div></article>"
            )
        return (
            "<section class='ai-market-header'><span>闭环流程</span>"
            "<strong>吸收 DataAgent 的 SOP、问数、归因和工作建议思想</strong></section>"
            "<div class='quant-flow-card-grid'>" + "".join(cards) + "</div>"
        )

    def quant_workflow_snapshot(
        self,
        mode: str,
        sop_id: str,
        strategy_id: Any,
        backtest_id: Any,
        account_id: Any,
        live_run_id: Any,
    ) -> tuple[str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        payload = QuantWorkflowService().snapshot(
            mode=str(mode or "simulation"),
            sop_id=str(sop_id or "") or None,
            strategy_id=_optional_id(strategy_id),
            backtest_id=_optional_id(backtest_id),
            account_id=_optional_id(account_id),
            live_run_id=_optional_id(live_run_id),
        )
        return self._workflow_outputs(payload)

    def quant_workflow_create_run(
        self,
        mode: str,
        sop_id: str,
        title: str,
        strategy_id: Any,
        backtest_id: Any,
        account_id: Any,
        live_run_id: Any,
    ) -> tuple[str, pd.DataFrame]:
        payload = {
            "mode": str(mode or "simulation"),
            "sop_id": str(sop_id or ""),
            "title": str(title or "").strip(),
            "strategy_id": _optional_id(strategy_id),
            "backtest_id": _optional_id(backtest_id),
            "account_id": _optional_id(account_id),
            "live_run_id": _optional_id(live_run_id),
        }
        run = QuantWorkflowService().create_run(payload)
        return compact_json(
            {"run_id": run["run_id"], "status": run["status"], "summary": run["summary"]}
        ), self.quant_workflow_runs(mode)

    def quant_workflow_runs(self, mode: str = "simulation") -> pd.DataFrame:
        result = QuantWorkflowService().list_runs(mode=str(mode or "simulation"), page=1, page_size=30)
        return to_frame(result.get("items") or [], QUANT_WORKFLOW_RUN_COLUMNS)

    def _workflow_outputs(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        summary = (
            f"### {payload['sop'].get('name', '闭环流程')}\n\n"
            f"{payload.get('summary', '')}\n\n"
            f"> {payload['sop'].get('description', '')}"
        )
        return (
            summary,
            self._workflow_board(payload),
            to_frame(_ordered_steps(payload.get("steps") or []), QUANT_WORKFLOW_STEP_COLUMNS),
            to_frame(payload.get("insights") or [], QUANT_WORKFLOW_INSIGHT_COLUMNS),
            to_frame(payload.get("questions") or [], QUANT_WORKFLOW_QUESTION_COLUMNS),
            to_frame(payload.get("advice") or [], QUANT_WORKFLOW_ADVICE_COLUMNS),
            to_frame(payload.get("artifacts") or [], QUANT_WORKFLOW_ARTIFACT_COLUMNS),
        )

    @staticmethod
    def _workflow_board(payload: dict[str, Any]) -> str:
        steps = []
        for index, step in enumerate(payload.get("steps") or [], start=1):
            status = str(step.get("status") or "not_started")
            steps.append(
                "<article class='quant-flow-step "
                + escape(status)
                + "'><b>"
                + f"{index:02d}"
                + "</b><div><small>"
                + escape(status)
                + "</small><strong>"
                + escape(str(step.get("title") or "-"))
                + "</strong><p>"
                + escape(str(step.get("evidence") or "-"))
                + "</p></div></article>"
            )
        insights = []
        for item in (payload.get("insights") or [])[:4]:
            severity = str(item.get("severity") or "info")
            insights.append(
                "<article class='quant-insight "
                + escape(severity)
                + "'><small>"
                + escape(str(item.get("title") or "-"))
                + "</small><strong>"
                + escape(str(item.get("conclusion") or "-"))
                + "</strong><p>"
                + escape(str(item.get("evidence") or "-"))
                + "</p></article>"
            )
        advice = []
        for item in (payload.get("advice") or [])[:3]:
            advice.append(
                "<li><b>"
                + escape(str(item.get("priority") or "-"))
                + "</b><span>"
                + escape(str(item.get("action") or "-"))
                + "</span><small>"
                + escape(str(item.get("next_step") or "-"))
                + "</small></li>"
            )
        return (
            "<section class='quant-workflow-board'>"
            "<div class='quant-flow-timeline'>"
            + "".join(steps)
            + "</div><div class='quant-flow-diagnosis'><div class='quant-insight-grid'>"
            + "".join(insights)
            + "</div><ol class='quant-advice-list'>"
            + "".join(advice)
            + "</ol></div></section>"
        )

    def ai_workbench_header(self) -> str:
        expert_count = len(_preset_items("experts"))
        team_count = len(_preset_items("team_presets"))
        job_count = len(_preset_items("job_templates"))
        task_count = len(_preset_items("task_types"))
        sop_count = len(_workflow_items("sops"))
        return (
            "<section class='ai-command-center'>"
            "<div class='ai-command-brand'><span>AIQuant Studio</span><strong>AI 工作台</strong>"
            "<p>按模拟模块、实盘模块、智能洞察和工作流中心组织完整投研工作流</p></div>"
            "<div class='ai-command-metrics'>"
            + self._command_metric("模拟模块", "6", "因子挖掘 / 策略 / 回测 / 归因")
            + self._command_metric("实盘模块", "2", "发布策略 / 归因分析")
            + self._command_metric("智能洞察", "2", "每日行情 / 问数")
            + self._command_metric("任务模式", str(task_count), "研究 / 策略 / 风控 / 编排")
            + self._command_metric("专家", str(expert_count), "单专家会话")
            + self._command_metric("专家团", str(team_count), "多角色协作")
            + self._command_metric("闭环SOP", str(sop_count), "模拟研究 / 真实观测")
            + self._command_metric("定时模板", str(job_count), "盘前盘中盘后流程")
            + "</div></section>"
        )

    @staticmethod
    def _command_metric(label: str, value: str, note: str) -> str:
        return (
            "<article class='ai-command-metric'><small>"
            + escape(label)
            + "</small><strong>"
            + escape(value)
            + "</strong><span>"
            + escape(note)
            + "</span></article>"
        )

    def ai_workbench_nav(self) -> str:
        items = [
            ("工作流总览", "入口与待办"),
            ("因子", "候选生成与验证"),
            ("任务会话", "固定对话区与上下文"),
            ("闭环", "归因和迭代建议"),
            ("专家", "按研究场景选择角色"),
            ("专家团", "负责人和成员分工"),
            ("能力", "Skill 与 MCP"),
            ("定时", "自动化任务链路"),
            ("知识", "RAG 问答"),
            ("CLI", "策略生成入口"),
        ]
        html = ["<aside class='ai-side-rail'><div class='ai-side-title'><span>工作区</span><strong>Flow</strong></div>"]
        for index, (label, note) in enumerate(items, start=1):
            html.append(
                "<div class='ai-side-item'><b>"
                + f"{index:02d}"
                + "</b><span>"
                + escape(label)
                + "</span><small>"
                + escape(note)
                + "</small></div>"
            )
        html.append("</aside>")
        return "".join(html)

    def ai_console_nav(self) -> pd.DataFrame:
        repo = Repository()
        rows = [
            {
                "入口": "新聊天",
                "数量": int(repo.db.scalar("SELECT COUNT(*) FROM ai_workspace_sessions") or 0),
                "最近状态": "可新建项目会话",
                "说明": "围绕当前项目保存模型对话历史",
            },
            {
                "入口": "定时任务",
                "数量": int(repo.db.scalar("SELECT COUNT(*) FROM scheduled_jobs") or 0),
                "最近状态": "任务模板可复用",
                "说明": "进入定时任务页配置盘前/盘中/盘后自动化",
            },
            {
                "入口": "Skill 包",
                "数量": int(repo.db.scalar("SELECT COUNT(*) FROM skills WHERE enabled = 1") or 0),
                "最近状态": "已启用",
                "说明": "进入 Skill 配置页启停与运行",
            },
            {
                "入口": "MCP 服务",
                "数量": int(repo.db.scalar("SELECT COUNT(*) FROM mcp_services WHERE enabled = 1") or 0),
                "最近状态": "已启用",
                "说明": "进入 MCP 服务页测试工具与连接",
            },
        ]
        return to_frame(rows, AI_WORKSPACE_NAV_COLUMNS)

    def ai_console_sessions(self) -> pd.DataFrame:
        rows = Repository().db.query(
            """
            SELECT id, project_name, title, session_type, status, updated_at
              FROM ai_workspace_sessions
             ORDER BY updated_at DESC, id DESC
             LIMIT 50
            """
        )
        for row in rows:
            row["updated_at"] = _format_display_time(row.get("updated_at"))
        return to_frame(rows, AI_WORKSPACE_SESSION_COLUMNS)

    def ai_console_new_session(
        self, title: str, project_name: str
    ) -> tuple[str, int, pd.DataFrame, list[dict[str, str]]]:
        item = AIWorkspaceService().create_session(
            str(title or "").strip() or "新的投研会话", str(project_name or "").strip() or None
        )
        return f"已新建会话 {item['title']}，ID={item['id']}", int(item["id"]), self.ai_console_sessions(), []

    def ai_console_load_session(self, session_id: Any) -> tuple[str, list[dict[str, str]]]:
        value = require_id(session_id, "会话 ID")
        session = Repository().get("ai_workspace_sessions", value)
        return (
            f"已载入会话 `{session.get('title')}`，ID={value}",
            self._ai_console_history(value),
        )

    def ai_console_send(
        self,
        session_id: Any,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
        backend_mode: str = AI_CONSOLE_GENERIC_BACKEND,
        attachments: Any = None,
        model_name: str = "",
        reasoning_effort: str = "",
        access_mode: str = "read-only",
    ) -> tuple[int, list[dict[str, str]], str, str, pd.DataFrame]:
        last = list(
            self.ai_console_send_stream(
                session_id, message, history, backend_mode, attachments, model_name, reasoning_effort, access_mode
            )
        )[-1]
        return last[0], last[1], last[2], last[4], last[5]

    def ai_console_send_ui(
        self,
        session_id: Any,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
        backend_mode: str = AI_CONSOLE_GENERIC_BACKEND,
        attachments: Any = None,
        model_name: str = "",
        reasoning_effort: str = "",
        access_mode: str = "read-only",
    ) -> tuple[int, list[dict[str, str]], str, list[str], str, pd.DataFrame]:
        result = self.ai_console_send(
            session_id,
            message,
            history,
            backend_mode,
            attachments,
            model_name,
            reasoning_effort,
            access_mode,
        )
        return result[0], result[1], result[2], [], result[3], result[4]

    def ai_console_send_stream(
        self,
        session_id: Any,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
        backend_mode: str = AI_CONSOLE_GENERIC_BACKEND,
        attachments: Any = None,
        model_name: str = "",
        reasoning_effort: str = "",
        access_mode: str = "read-only",
    ):
        content = require_text(message, "消息内容")
        value = int(session_id or 0)
        if value <= 0:
            value = int(self.ai_console_new_session(content[:24], "")[1])
        backend = self._normalize_ai_console_backend(backend_mode)
        payload = {
            "message": content,
            "backend": backend,
            "model_id": self._model_id_for_name(model_name) if backend == AI_CONSOLE_GENERIC_BACKEND else None,
            "model_name": model_name,
            "reasoning_effort": reasoning_effort,
            "access_mode": access_mode,
        }
        base_history = self._ai_console_history(value)
        partial = ""
        label = "GenericAgent" if backend == AI_CONSOLE_GENERIC_BACKEND else CLI_PROVIDERS.get(backend, backend)
        stream = AIWorkspaceService().send_stream(value, payload, local_attachments=attachments)
        try:
            first = next(stream)
        except BusinessError as exc:
            # A rejected attachment must not turn every output into a Gradio error panel.
            yield value, base_history, content, gr.skip(), f"未发送 · {exc.message}", self.ai_console_sessions()
            return
        for event in chain((first,), stream):
            details = event["data"]
            if event["type"] == "message":
                partial += str(details.get("text") or "")
            if event["type"] == "result":
                result = details["data"]
                failed = result.get("status") in {"failed", "timeout", "unavailable", "mock-disabled"}
                yield (
                    value,
                    self._ai_console_history(value),
                    content if failed else "",
                    gr.skip() if failed else [],
                    f"{label} {result.get('status')} · 会话 ID={value} · {result.get('text', '')[:160]}",
                    self.ai_console_sessions(),
                )
            else:
                shown = base_history + [{"role": "user", "content": content}]
                if partial:
                    shown.append({"role": "assistant", "content": partial})
                yield (
                    value,
                    shown,
                    gr.skip(),
                    gr.skip(),
                    f"{label} {details.get('status', 'running')} · 会话 ID={value}",
                    self.ai_console_sessions(),
                )

    @staticmethod
    def _model_id_for_name(model_name: str) -> int | None:
        text = str(model_name or "").strip()
        if not text:
            return None
        row = Repository().db.query_one("SELECT id FROM llm_models WHERE enabled = 1 AND model_name = ?", (text,))
        return int(row["id"]) if row else None

    @staticmethod
    def _normalize_ai_console_backend(value: Any) -> str:
        return normalize_backend(value)

    @staticmethod
    def _resolve_project_path(relative_path: str) -> tuple[Path, str]:
        text = str(relative_path or "").strip() or "."
        root = PROJECT_ROOT.resolve()
        target = (root / text).resolve()
        try:
            display_path = target.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("只能访问项目目录内的文件") from exc
        return target, display_path

    def ai_console_file_preview(self, relative_path: str) -> str:
        target, display_path = self._resolve_project_path(relative_path or "README.md")
        root = PROJECT_ROOT.resolve()
        if not target.exists():
            raise ValueError("文件不存在")
        if target.is_dir():
            children = sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))[:80]
            lines = [f"# {display_path or '.'}", ""]
            for child in children:
                marker = "FILE" if child.is_file() else "DIR "
                lines.append(f"- {marker} `{child.relative_to(root).as_posix()}`")
            return "\n".join(lines)
        if target.stat().st_size > 512_000:
            raise ValueError("文件超过 512KB，请选择更小的源码或文档文件")
        if target.suffix.lower() not in AI_PROJECT_TEXT_SUFFIXES and target.name not in {".env.example", "README.md"}:
            raise ValueError("当前仅预览源码、配置、Markdown、CSV 等文本文件")
        project_file(display_path)
        return target.read_text(encoding="utf-8", errors="replace")

    def _ai_console_history(self, session_id: int) -> list[dict[str, str]]:
        rows = AIWorkspaceService().detail(session_id)["messages"]
        values = []
        for row in rows:
            if row["role"] not in {"user", "assistant"}:
                continue
            content = str(row["content"])
            if row["role"] == "user":
                documents = row.get("metadata", {}).get("attachments", {}).get("documents", [])
                for document in documents:
                    name = str(document["name"]).replace("[", "［").replace("]", "］")
                    content += f"\n\n📎 [{name}]({get_settings().api_prefix}/file-previews/{document['id']}/view)"
            values.append({"role": str(row["role"]), "content": content})
        return values

    def ai_console_project_tree(self, relative_dir: str = "") -> tuple[str, pd.DataFrame, str]:
        target, display_path = self._resolve_project_path(relative_dir or ".")
        if target.is_file():
            target = target.parent
            display_path = target.relative_to(PROJECT_ROOT.resolve()).as_posix() or "."
        if not target.exists():
            raise ValueError("目录不存在")
        if not target.is_dir():
            raise ValueError("请选择项目目录")

        root = PROJECT_ROOT.resolve()
        rows: list[dict[str, Any]] = []
        if target != root:
            parent_path = target.parent.relative_to(root).as_posix() or "."
            rows.append({"类型": "上级", "路径": parent_path, "说明": "返回上级目录"})
        children = sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        for child in children:
            if (
                child.name in AI_PROJECT_IGNORED_NAMES
                or child.name.startswith((".tmp", ".venv"))
                or child.name in preview_config()["project"]["blocked_parts"]
            ):
                continue
            if len(rows) >= AI_PROJECT_TREE_LIMIT:
                break
            child_path = child.relative_to(root).as_posix()
            if child.is_dir():
                rows.append({"类型": "目录", "路径": child_path, "说明": "打开目录"})
                continue
            suffix = child.suffix.lower()
            allowed = {ext for group in preview_config()["formats"].values() for ext in group}
            if suffix not in allowed and child.name not in {".env.example", "README.md"}:
                continue
            try:
                project_file(child_path)
            except BusinessError:
                continue
            size_kb = max(1, round(child.stat().st_size / 1024))
            rows.append({"类型": "文件", "路径": child_path, "说明": f"{suffix or '文本'} · {size_kb}KB"})
        status = f"项目目录 `{display_path or '.'}` 已加载，展示 {len(rows)} 项。"
        return status, to_frame(rows, AI_PROJECT_FILE_COLUMNS), display_path or "."

    def ai_workbench_overview(self, account_mode: str = "paper") -> str:
        mode = _normalize_account_mode(account_mode)
        account_label = _choice_label(ACCOUNT_MODE_CHOICES, mode)
        repo = Repository()
        latest_runs = repo.db.query("SELECT * FROM quant_workflow_runs ORDER BY created_at DESC LIMIT 3")
        open_alerts = int(repo.db.scalar("SELECT COUNT(*) FROM factor_alerts WHERE status = 'open'") or 0)
        enabled_skills = int(repo.db.scalar("SELECT COUNT(*) FROM skills WHERE enabled = 1") or 0)
        enabled_mcps = int(repo.db.scalar("SELECT COUNT(*) FROM mcp_services WHERE enabled = 1") or 0)
        running_live = int(repo.db.scalar("SELECT COUNT(*) FROM live_runs WHERE status = 'running'") or 0)
        metric_html = "".join(
            self._overview_metric(label, value, note)
            for label, value, note in [
                ("当前视角", account_label, "总览入口同步此口径"),
                ("因子告警", str(open_alerts), "打开状态"),
                ("运行策略", str(running_live), "实盘/模拟通道记录"),
                ("Skill/MCP", f"{enabled_skills}/{enabled_mcps}", "启用能力"),
            ]
        )
        lane_html = "".join(
            self._overview_lane(
                title,
                subtitle,
                stages,
                action,
            )
            for title, subtitle, stages, action in [
                (
                    "模拟研究闭环",
                    "分析 → 构建策略 → 模拟 → 归因 → 优化迭代",
                    ["因子有效性", "策略版本", "回测绩效", "迭代建议"],
                    "生成闭环快照",
                ),
                (
                    "真实交易观测闭环",
                    "交易 → 观测 → 归因 → 迭代建议",
                    ["运行状态", "订单持仓", "风险暴露", "人工复核"],
                    "查看交易观测",
                ),
                (
                    "专家协作入口",
                    "单专家、专家团、Skill 与 MCP 组合执行",
                    ["专家候选", "专家团分工", "能力状态", "任务模板"],
                    "选择专家",
                ),
            ]
        )
        recent_html = []
        for run in latest_runs:
            recent_html.append(
                "<article><small>"
                + escape(str(run.get("mode") or "-"))
                + "</small><strong>"
                + escape(str(run.get("title") or "-"))
                + "</strong><p>"
                + escape(str(run.get("summary") or "-"))
                + "</p></article>"
            )
        if not recent_html:
            recent_html.append(
                "<article><small>暂无历史</small><strong>等待第一次闭环运行</strong><p>进入闭环流程后保存运行，历史会显示在这里。</p></article>"
            )
        return (
            "<section class='ai-workbench-overview'>"
            "<div class='ai-overview-hero'><span>AI 工作台总览</span>"
            "<strong>投研闭环、专家协作和自动化任务的主入口</strong>"
            "<button type='button' class='ai-workbench-entry-action'>回到工作台</button></div>"
            "<div class='ai-overview-metrics'>"
            + metric_html
            + "</div><div class='ai-overview-lanes'>"
            + lane_html
            + "</div><section class='ai-overview-recent'><header><span>最近闭环运行</span><b>"
            + str(len(latest_runs))
            + "</b></header><div>"
            + "".join(recent_html)
            + "</div></section></section>"
        )

    @staticmethod
    def _overview_metric(label: str, value: str, note: str) -> str:
        return (
            "<article><small>"
            + escape(label)
            + "</small><strong>"
            + escape(value)
            + "</strong><span>"
            + escape(note)
            + "</span></article>"
        )

    @staticmethod
    def _overview_lane(title: str, subtitle: str, stages: Sequence[str], action: str) -> str:
        stage_html = "".join("<span>" + escape(stage) + "</span>" for stage in stages)
        return (
            "<article class='ai-overview-lane'><small>"
            + escape(subtitle)
            + "</small><strong>"
            + escape(title)
            + "</strong><div>"
            + stage_html
            + "</div><button type='button' class='ai-workbench-entry-action'>"
            + escape(action)
            + "</button></article>"
        )

    def ai_experts(self, group: str = "all") -> pd.DataFrame:
        selected_group = str(group or "all")
        group_labels = {value: label for label, value in AI_EXPERT_GROUP_CHOICES}
        task_labels = {value: label for label, value in AI_TASK_TYPE_CHOICES}
        rows = []
        for expert in _preset_items("experts"):
            if selected_group != "all" and str(expert.get("group")) != selected_group:
                continue
            rows.append(
                {
                    "expert_id": expert.get("id"),
                    "name": expert.get("name"),
                    "group": group_labels.get(str(expert.get("group")), str(expert.get("group") or "-")),
                    "focus": expert.get("focus"),
                    "starter": expert.get("starter"),
                    "deliverable": expert.get("deliverable"),
                    "task_type": task_labels.get(str(expert.get("task_type")), str(expert.get("task_type") or "-")),
                }
            )
        return to_frame(rows, AI_EXPERT_COLUMNS)

    def ai_expert_catalog(self, group: str = "all") -> tuple[str, pd.DataFrame]:
        return self.ai_expert_cards(group), self.ai_experts(group)

    def ai_expert_cards(self, group: str = "all") -> str:
        selected_group = str(group or "all")
        group_labels = {value: label for label, value in AI_EXPERT_GROUP_CHOICES}
        task_labels = {value: label for label, value in AI_TASK_TYPE_CHOICES}
        cards = []
        for expert in _preset_items("experts"):
            expert_group = str(expert.get("group") or "")
            if selected_group != "all" and expert_group != selected_group:
                continue
            name = escape(str(expert.get("name") or "-"))
            focus = escape(str(expert.get("focus") or "-"))
            starter = escape(str(expert.get("starter") or "-"))
            deliverable = escape(str(expert.get("deliverable") or "-"))
            group_label = escape(group_labels.get(expert_group, expert_group or "-"))
            task_label = escape(task_labels.get(str(expert.get("task_type")), str(expert.get("task_type") or "-")))
            skills = expert.get("skills") or []
            skill_line = (
                "、".join(str(item) for item in skills[:3]) if isinstance(skills, list) and skills else "按任务检查"
            )
            cards.append(
                "<article class='ai-agent-card ai-launch-card'>"
                "<div class='ai-agent-card-top'><span class='ai-agent-mark'>AI</span>"
                "<span class='ai-agent-badge'>"
                + group_label
                + "</span></div><h3>"
                + name
                + "</h3><p>"
                + focus
                + "</p><div class='ai-agent-meta'><span>"
                + task_label
                + "</span><span>可带入任务对话</span></div><div class='ai-agent-starter'><small>试试这个问题</small><strong>"
                + starter
                + "</strong></div><div class='ai-agent-delivery'><b>交付</b>"
                + deliverable
                + "</div><div class='ai-agent-skill-line'><b>能力</b><span>"
                + escape(skill_line)
                + "</span></div><footer><span>开始新对话</span><span>查看配置</span></footer>"
                + "</article>"
            )
        if not cards:
            return "<div class='ai-empty-state'>当前分组暂无专家预设。</div>"
        return (
            "<section class='ai-market-header'><span>专家市场</span><strong>选择专家后带入任务会话</strong></section>"
            "<div class='ai-agent-grid'>" + "".join(cards) + "</div>"
        )

    def ai_expert_detail(self, expert_id: str) -> str:
        expert = _preset_by_id("experts", expert_id)
        if not expert:
            return "未找到专家预设。"
        group_label = _choice_label(AI_EXPERT_GROUP_CHOICES, expert.get("group"))
        task_label = _choice_label(AI_TASK_TYPE_CHOICES, expert.get("task_type"))
        return (
            f"### {expert.get('name', '-')}\n\n"
            f"- 分组：{group_label}\n"
            f"- 默认任务：{task_label}\n"
            f"- 关注点：{expert.get('focus', '-')}\n"
            f"- 交付物：{expert.get('deliverable', '-')}\n"
            f"- 示例输入：{expert.get('starter', '-')}\n\n"
            f"{expert.get('instruction', '')}"
        )

    def ai_teams(self, group: str = "all") -> pd.DataFrame:
        selected_group = str(group or "all")
        group_labels = {value: label for label, value in AI_EXPERT_GROUP_CHOICES}
        rows = []
        for team in _preset_items("team_presets"):
            team_group = str(team.get("group") or "")
            if selected_group != "all" and team_group != selected_group:
                continue
            lead = self._expert_name(team.get("lead"))
            members = self._team_member_names(team.get("members") or [])
            rows.append(
                {
                    "team_id": team.get("id"),
                    "name": team.get("name"),
                    "group": group_labels.get(team_group, team_group or "-"),
                    "lead": lead,
                    "members": "、".join(members),
                    "summary": team.get("summary"),
                    "starter": team.get("starter"),
                    "deliverable": team.get("deliverable"),
                }
            )
        return to_frame(rows, AI_TEAM_COLUMNS)

    @staticmethod
    def _expert_name(expert_id: Any) -> str:
        expert = _preset_by_id("experts", expert_id)
        return str(expert.get("name") or expert_id or "-")

    def _team_member_names(self, members: Any) -> list[str]:
        result: list[str] = []
        if not isinstance(members, list):
            return result
        for member in members:
            if isinstance(member, dict):
                result.append(self._expert_name(member.get("expert")))
        return result

    def ai_team_catalog(self, group: str = "all") -> tuple[str, pd.DataFrame]:
        return self.ai_team_cards(group), self.ai_teams(group)

    def ai_team_cards(self, group: str = "all") -> str:
        selected_group = str(group or "all")
        group_labels = {value: label for label, value in AI_EXPERT_GROUP_CHOICES}
        cards = []
        for team in _preset_items("team_presets"):
            team_group = str(team.get("group") or "")
            if selected_group != "all" and team_group != selected_group:
                continue
            name = escape(str(team.get("name") or "-"))
            summary = escape(str(team.get("summary") or "-"))
            starter = escape(str(team.get("starter") or "-"))
            deliverable = escape(str(team.get("deliverable") or "-"))
            group_label = escape(group_labels.get(team_group, team_group or "-"))
            lead_name = escape(self._expert_name(team.get("lead")))
            member_names = self._team_member_names(team.get("members") or [])
            member_tags = "".join("<span>" + escape(name) + "</span>" for name in member_names[:5])
            stages = team.get("stages") or []
            stage_items = "".join("<li>" + escape(str(stage)) + "</li>" for stage in stages[:4] if str(stage).strip())
            cards.append(
                "<article class='ai-team-card ai-launch-card'>"
                "<div class='ai-agent-card-top'><span class='ai-agent-mark'>TEAM</span>"
                "<span class='ai-agent-badge'>"
                + group_label
                + "</span></div><h3>"
                + name
                + "</h3><p>"
                + summary
                + "</p><div class='ai-team-roster'><b>负责人 · "
                + lead_name
                + "</b><div>"
                + member_tags
                + "</div></div><div class='ai-agent-starter'><small>试试这个任务</small><strong>"
                + starter
                + "</strong></div><ol class='ai-team-flow'>"
                + stage_items
                + "</ol><div class='ai-agent-delivery'><b>交付</b>"
                + deliverable
                + "</div><footer><span>开始团队会话</span><span>查看分工</span></footer></article>"
            )
        if not cards:
            return "<div class='ai-empty-state'>当前分组暂无专家团预设。</div>"
        return (
            "<section class='ai-market-header'><span>专家团</span><strong>按负责人、成员和流程协作</strong></section>"
            "<div class='ai-team-grid'>" + "".join(cards) + "</div>"
        )

    def ai_team_detail(self, team_id: str) -> str:
        team = _preset_by_id("team_presets", team_id)
        if not team:
            return "未找到专家团预设。"
        group_label = _choice_label(AI_EXPERT_GROUP_CHOICES, team.get("group"))
        members = []
        for member in team.get("members") or []:
            if not isinstance(member, dict):
                continue
            members.append(f"- {self._expert_name(member.get('expert'))}：{member.get('responsibility', '-')}")
        stages = [f"{index}. {stage}" for index, stage in enumerate(team.get("stages") or [], start=1)]
        return (
            f"### {team.get('name', '-')}\n\n"
            f"- 分组：{group_label}\n"
            f"- 负责人：{self._expert_name(team.get('lead'))}\n"
            f"- 交付物：{team.get('deliverable', '-')}\n"
            f"- 示例输入：{team.get('starter', '-')}\n\n"
            f"**成员分工**\n\n{chr(10).join(members) or '-'}\n\n"
            f"**执行流程**\n\n{chr(10).join(stages) or '-'}"
        )

    def ai_team_to_task_state(self, team_id: str, account_mode: str) -> tuple[str, str, str, str, str]:
        team = _preset_by_id("team_presets", team_id)
        lead_id = str(team.get("lead") or (AI_EXPERT_CHOICES[0][1] if AI_EXPERT_CHOICES else ""))
        lead = _preset_by_id("experts", lead_id)
        task_type = str(team.get("task_type") or lead.get("task_type") or "research")
        starter = str(team.get("starter") or "")
        team_name = str(team.get("name") or "专家团")
        prompt = f"{starter}\n\n请按「{team_name}」专家团的负责人和成员分工推进，先给执行计划、数据口径和交付清单。"
        brief = self.ai_workbench_brief(task_type, account_mode, lead_id)
        return task_type, lead_id, prompt, brief, self.ai_workbench_context(task_type, account_mode, lead_id, team_id)

    def ai_capability_catalog(self) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        callbacks = cast(CrossDomainCallbacks, self)
        skills = callbacks.skills()
        mcps = callbacks.mcp_servers()
        return self.ai_capability_cards(skills, mcps), skills, mcps

    def ai_capability_cards(
        self,
        skills: pd.DataFrame | None = None,
        mcps: pd.DataFrame | None = None,
    ) -> str:
        callbacks = cast(CrossDomainCallbacks, self)
        skill_frame = skills if skills is not None else callbacks.skills()
        mcp_frame = mcps if mcps is not None else callbacks.mcp_servers()
        enabled_skills = self._count_enabled_rows(skill_frame)
        enabled_mcps = self._count_enabled_rows(mcp_frame)
        cards = [
            (
                "Skill 包",
                f"{enabled_skills}/{len(skill_frame)}",
                "投研、策略、报告和自动化能力包",
                "active" if enabled_skills else "muted",
            ),
            (
                "MCP 工具",
                f"{enabled_mcps}/{len(mcp_frame)}",
                "连接远程知识库、外部工具和桌面能力",
                "active" if enabled_mcps else "muted",
            ),
            (
                "专家预设",
                str(len(_preset_items("experts"))),
                "从任务类型和账户视角生成对话上下文",
                "active",
            ),
            (
                "任务模板",
                str(len(_preset_items("job_templates"))),
                "把常见研究流程转换成定时任务",
                "active",
            ),
        ]
        html = []
        for label, value, summary, tone in cards:
            html.append(
                "<article class='ai-capability-card "
                + tone
                + "'><small>"
                + escape(label)
                + "</small><strong>"
                + escape(value)
                + "</strong><span>"
                + escape(summary)
                + "</span></article>"
            )
        html.append("</div>")
        html.append("<div class='ai-capability-library'>")
        html.append(self._capability_rows("Skill 包", skill_frame, ("name", "skill_name", "title"), ("enabled",)))
        html.append(
            self._capability_rows(
                "MCP 工具",
                mcp_frame,
                ("name", "service_name", "server_name"),
                ("enabled", "is_enabled"),
            )
        )
        html.append("</div>")
        return (
            "<section class='ai-market-header'><span>能力设置</span>"
            "<strong>Skill、MCP、专家和任务模板统一纳入工作台</strong></section>"
            "<div class='ai-capability-grid'>" + "".join(html)
        )

    @staticmethod
    def _count_enabled_rows(frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        for column in ("enabled", "is_enabled", "启用"):
            if column in frame.columns:
                return int(sum(bool(value) for value in frame[column].tolist()))
        return len(frame)

    @staticmethod
    def _capability_rows(
        title: str,
        frame: pd.DataFrame,
        name_columns: Sequence[str],
        enabled_columns: Sequence[str],
    ) -> str:
        if frame.empty:
            return (
                "<section class='ai-capability-list'><header><b>"
                + escape(title)
                + "</b><span>0</span></header><div class='ai-empty-state'>暂无配置。</div></section>"
            )
        rows = []
        for record in frame.head(5).to_dict(orient="records"):
            name = "-"
            for column in name_columns:
                if column in record and record.get(column):
                    name = str(record.get(column))
                    break
            enabled = True
            for column in enabled_columns:
                if column in record:
                    enabled = bool(record.get(column))
                    break
            status = "启用" if enabled else "停用"
            rows.append(
                "<div class='ai-capability-row'><span>"
                + escape(name)
                + "</span><b class='"
                + ("active" if enabled else "muted")
                + "'>"
                + status
                + "</b></div>"
            )
        return (
            "<section class='ai-capability-list'><header><b>"
            + escape(title)
            + "</b><span>"
            + str(len(frame))
            + "</span></header>"
            + "".join(rows)
            + "</section>"
        )

    def ai_workbench_state(self, task_type: str, account_mode: str, expert_id: str) -> tuple[str, str]:
        return self.ai_workbench_brief(task_type, account_mode, expert_id), self.ai_workbench_context(
            task_type,
            account_mode,
            expert_id,
        )

    def ai_workbench_brief(self, task_type: str, account_mode: str, expert_id: str) -> str:
        task = _preset_by_id("task_types", _normalize_ai_task_type(task_type))
        mode = _normalize_account_mode(account_mode)
        account = _preset_by_id("account_modes", mode)
        expert = _preset_by_id("experts", expert_id)
        expert_name = expert.get("name") or "未选择专家"
        return (
            f"**AI工作台**  ·  任务 `{task.get('label', '-')}`  ·  账户视角 `{account.get('label', '-')}`  ·  "
            f"专家 `{expert_name}`\n\n"
            f"{task.get('instruction', '')}\n\n"
            f"> {account.get('summary', '')}"
        )

    def ai_workbench_context(
        self,
        task_type: str,
        account_mode: str,
        expert_id: str,
        team_id: str | None = None,
    ) -> str:
        task = _preset_by_id("task_types", _normalize_ai_task_type(task_type))
        mode = _normalize_account_mode(account_mode)
        account = _preset_by_id("account_modes", mode)
        expert = _preset_by_id("experts", expert_id)
        team = _preset_by_id("team_presets", team_id) if team_id else {}
        expert_name = escape(str(expert.get("name") or "通用助手"))
        task_label = escape(str(task.get("label") or "-"))
        account_label = escape(str(account.get("label") or "-"))
        starter = escape(str(expert.get("starter") or "描述你的研究、策略、风控或任务编排目标"))
        focus = escape(str(expert.get("focus") or task.get("instruction") or "-"))
        deliverable = escape(str(expert.get("deliverable") or "结论、依据、下一步"))
        account_summary = escape(str(account.get("summary") or "-"))
        skills = expert.get("skills") or []
        skill_line = (
            "、".join(str(item) for item in skills[:4]) if isinstance(skills, list) and skills else "按任务动态检查"
        )
        team_name = escape(str(team.get("name") or "单专家会话"))
        team_members = self._team_member_names(team.get("members") or [])
        team_line = "、".join(team_members[:4]) if team_members else "无团队成员"
        return (
            "<aside class='ai-context-board'>"
            "<div class='ai-context-title'><span>上下文</span><strong>" + expert_name + "</strong></div>"
            "<div class='ai-context-matrix'>"
            "<div><small>任务</small><b>"
            + task_label
            + "</b></div><div><small>账户</small><b>"
            + account_label
            + "</b></div></div>"
            "<div class='ai-context-block'><small>关注重点</small><p>"
            + focus
            + "</p></div><div class='ai-context-block'><small>交付物</small><p>"
            + deliverable
            + "</p></div><div class='ai-context-block'><small>账户口径</small><p>"
            + account_summary
            + "</p></div><div class='ai-context-block'><small>协作模式</small><p>"
            + team_name
            + " · "
            + escape(team_line)
            + "</p></div><div class='ai-context-block'><small>能力口径</small><p>"
            + escape(skill_line)
            + "</p></div><div class='ai-context-starter'><small>推荐开场</small><strong>"
            + starter
            + "</strong></div></aside>"
        )

    def ai_expert_to_task(self, expert_id: str, account_mode: str) -> tuple[str, str, str, str]:
        expert = _preset_by_id("experts", expert_id)
        task_type = str(expert.get("task_type") or "general")
        selected_id = str(expert.get("id") or expert_id)
        starter = str(expert.get("starter") or "")
        return task_type, selected_id, starter, self.ai_workbench_brief(task_type, account_mode, selected_id)

    def ai_expert_to_task_state(self, expert_id: str, account_mode: str) -> tuple[str, str, str, str, str]:
        task_type, selected_id, starter, brief = self.ai_expert_to_task(expert_id, account_mode)
        return (
            task_type,
            selected_id,
            starter,
            brief,
            self.ai_workbench_context(
                task_type,
                account_mode,
                selected_id,
            ),
        )

    def ai_workbench_chat(
        self,
        task_type: str,
        account_mode: str,
        expert_id: str,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
    ) -> tuple[list[dict[str, str]], str, str]:
        question = require_text(message, "任务内容")
        selected_task_type = _normalize_ai_task_type(task_type)
        selected_account_mode = _normalize_account_mode(account_mode)
        task = _preset_by_id("task_types", selected_task_type)
        account = _preset_by_id("account_modes", selected_account_mode)
        expert = _preset_by_id("experts", expert_id)
        expert_instruction = str(expert.get("instruction") or "")
        context = "\n".join(
            [
                "你在 AIQuant智投的 AI工作台中协助用户。",
                f"任务类型：{task.get('label', selected_task_type)}。{task.get('instruction', '')}",
                f"账户视角：{account.get('label', selected_account_mode)}。{account.get('summary', '')}",
                f"专家角色：{expert.get('name', '通用助手')}。{expert_instruction}",
                "输出需要先给结论和下一步，再列关键假设、数据口径和风险边界。",
                "涉及实盘账户时必须说明当前系统是否只是配置占位，不得承诺收益或暗示已完成真实下单。",
            ]
        )
        messages = _chat_history_messages(history)
        result = LLMClient().complete(f"{context}\n\n用户任务：{question}", purpose="AI工作台", history=messages)
        messages.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["text"]},
            ]
        )
        status = (
            f"`{result['model']}` · {result['duration_ms']} ms · {task.get('label', '-')} / {account.get('label', '-')}"
        )
        return messages, "", status

    def ai_job_catalog(self) -> tuple[str, pd.DataFrame]:
        return self.ai_job_template_cards(), self.ai_job_templates()

    def ai_job_template_cards(self) -> str:
        cards = []
        for template in _preset_items("job_templates"):
            label = escape(str(template.get("label") or template.get("name") or "-"))
            job_type = escape(str(template.get("job_type") or "-"))
            cron = escape(str(template.get("cron") or "-"))
            enabled = bool(template.get("enabled", True))
            params = template.get("params") or {}
            params_text = escape(", ".join(f"{key}={value}" for key, value in params.items()) or "-")
            status = "启用" if enabled else "停用"
            tone = "active" if enabled else "muted"
            cards.append(
                "<article class='ai-job-card "
                + tone
                + "'><div class='ai-job-card-top'><span>"
                + status
                + "</span><b>"
                + job_type
                + "</b></div><h3>"
                + label
                + "</h3><div class='ai-job-cron'>"
                + cron
                + "</div><p>"
                + params_text
                + "</p></article>"
            )
        if not cards:
            return "<div class='ai-empty-state'>暂无定时任务模板。</div>"
        return (
            "<section class='ai-market-header'><span>任务模板</span><strong>先套用模板，再按账户和策略调整</strong></section>"
            "<div class='ai-job-grid'>" + "".join(cards) + "</div>"
        )

    def ai_job_templates(self) -> pd.DataFrame:
        rows = []
        for template in _preset_items("job_templates"):
            rows.append(
                {
                    "template_id": template.get("id"),
                    "label": template.get("label"),
                    "job_type": template.get("job_type"),
                    "cron": template.get("cron"),
                    "enabled": bool(template.get("enabled", True)),
                    "params": template.get("params") or {},
                }
            )
        return to_frame(rows, AI_JOB_TEMPLATE_COLUMNS)

    def ai_job_template_form(self, template_id: str) -> tuple[str, str, str, str, bool]:
        template = _preset_by_id("job_templates", template_id)
        return (
            str(template.get("name") or template.get("label") or ""),
            str(template.get("job_type") or "custom"),
            str(template.get("cron") or "*/10 * * * *"),
            compact_json(template.get("params") or {}),
            bool(template.get("enabled", True)),
        )
