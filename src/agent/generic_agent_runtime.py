"""GenericAgent-style REACT runtime for the Gradio AI workbench.

The control loop is adapted from the MIT-licensed GenericAgent project at
``E:/Git_Prj/agent/personal_assitant/GenericAgent``.  This project keeps the
implementation local, loguru-based, and bounded to the current workspace.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from json_repair import loads as repair_json_loads

from src.agent.langfuse_observer import LangfuseObserver
from src.agent.llm_client import LLMClient
from src.core.config import PROJECT_ROOT
from src.core.logger import get_logger
from src.core.repository import Repository

LOG = get_logger("agent.generic_agent")
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "egs" / "config" / "agents" / "generic_agent.yaml"
TOOL_BLOCK_PATTERN = re.compile(r"<tool_use>(.*?)</tool_use>", re.DOTALL | re.IGNORECASE)


@dataclass(slots=True)
class GenericToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass(slots=True)
class ToolExecution:
    tool_name: str
    status: str
    content: str
    should_exit: bool = False
    needs_user: bool = False


@dataclass(slots=True)
class GenericAgentResult:
    text: str
    model: str
    duration_ms: int
    turns: int
    tool_events: list[dict[str, str]] = field(default_factory=list)
    needs_user: bool = False


class GenericAgentRuntime:
    """Small, project-safe GenericAgent adapter for OpenAI-compatible models."""

    def __init__(
        self,
        *,
        repo: Repository | None = None,
        llm: LLMClient | None = None,
        project_root: Path | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.llm = llm or LLMClient(repo=self.repo)
        self.project_root = (project_root or PROJECT_ROOT).resolve()
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.config = self._load_config(self.config_path)
        self.max_turns = _bounded_int(self.config.get("max_turns"), 3, 1, 12)
        self.max_history_messages = _bounded_int(self.config.get("max_history_messages"), 12, 0, 30)
        self.max_tool_output_chars = _bounded_int(self.config.get("max_tool_output_chars"), 12000, 1000, 50000)
        self.max_file_read_lines = _bounded_int(self.config.get("max_file_read_lines"), 240, 20, 2000)
        self.text_suffixes = {str(item).lower() for item in self.config.get("text_suffixes", [])}
        self.ignored_names = {str(item) for item in self.config.get("ignored_names", [])}
        observability = self.config.get("observability") if isinstance(self.config.get("observability"), dict) else {}
        langfuse_config = observability.get("langfuse") if isinstance(observability, dict) else {}
        self.observer = LangfuseObserver.from_config(langfuse_config if isinstance(langfuse_config, dict) else {})

    def run_once(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        *,
        session_id: int | str | None = None,
        model_id: int | None = None,
        reasoning_effort: str | None = None,
        image_paths: list[str] | None = None,
    ) -> GenericAgentResult:
        """Run a bounded REACT loop and return the final answer plus tool trace."""

        started = time.perf_counter()
        visible_text = ""
        model_name = "-"
        tool_events: list[dict[str, str]] = []
        llm_history = list(history or [])[-self.max_history_messages :]
        next_user_content = message
        needs_user = False
        turns_used = 0
        LOG.info("generic agent session started | turns={} root={}", self.max_turns, self.project_root)
        with self.observer.agent_run(
            message=message,
            session_id=session_id,
            project_root=self.project_root,
            history_count=len(history or []),
        ) as agent_observation:
            try:
                for turn in range(1, self.max_turns + 1):
                    turns_used = turn
                    prompt = self._build_prompt(next_user_content, tool_events)
                    with self.observer.generation(
                        turn=turn, prompt=prompt, history_count=len(llm_history)
                    ) as generation:
                        llm_kwargs: dict[str, Any] = {"history": llm_history}
                        if model_id is not None:
                            llm_kwargs["model_id"] = model_id
                        if reasoning_effort:
                            llm_kwargs["reasoning_effort"] = reasoning_effort
                        if image_paths:
                            llm_kwargs["image_paths"] = image_paths
                        result = self.llm.complete(prompt, purpose="AI工作台-GenericAgent", **llm_kwargs)
                        model_name = str(result.get("model") or model_name)
                        response_text = str(result.get("text") or "").strip()
                        generation.finish(
                            output=response_text,
                            model=model_name,
                            usage=result.get("usage") or {},
                            metadata={
                                "turn": turn,
                                "duration_ms": int(result.get("duration_ms") or 0),
                                "response_chars": len(response_text),
                            },
                        )
                    cleaned_text, calls = self._extract_tool_calls(response_text)
                    if cleaned_text:
                        visible_text = cleaned_text
                    llm_history.extend(
                        [
                            {"role": "user", "content": next_user_content},
                            {"role": "assistant", "content": response_text},
                        ]
                    )
                    LOG.info(
                        "generic agent turn completed | turn={} model={} tool_calls={}",
                        turn,
                        model_name,
                        len(calls),
                    )
                    if not calls:
                        break
                    next_parts: list[str] = []
                    for call in calls:
                        with self.observer.tool(tool_name=call.name, arguments=call.arguments) as tool_observation:
                            execution = self.dispatch_tool(call)
                            tool_observation.finish(
                                output=execution.content,
                                metadata={
                                    "tool": execution.tool_name,
                                    "status": execution.status,
                                    "content_chars": len(execution.content or ""),
                                    "needs_user": execution.needs_user,
                                    "should_exit": execution.should_exit,
                                },
                            )
                        tool_events.append(
                            {
                                "tool": execution.tool_name,
                                "status": execution.status,
                                "content": self._clip_text(execution.content, 1600),
                            }
                        )
                        next_parts.append(
                            f'<tool_result name="{execution.tool_name}" status="{execution.status}">\n'
                            f"{execution.content}\n</tool_result>"
                        )
                        if execution.needs_user:
                            needs_user = True
                        if execution.should_exit:
                            visible_text = execution.content
                            break
                    if needs_user or (tool_events and tool_events[-1]["tool"] == "finish"):
                        break
                    next_user_content = self._continue_prompt(next_parts)
                else:
                    tool_events.append(
                        {"tool": "loop_guard", "status": "stopped", "content": "已达到最大轮数，停止继续调用。"}
                    )
                    LOG.warning("generic agent reached max turns | turns={}", self.max_turns)
                if tool_events:
                    visible_text = self._append_tool_trace(visible_text, tool_events)
                duration_ms = round((time.perf_counter() - started) * 1000)
                LOG.info(
                    "generic agent session finished | model={} duration_ms={} tools={} needs_user={}",
                    model_name,
                    duration_ms,
                    len(tool_events),
                    needs_user,
                )
                final_text = visible_text or "GenericAgent 未返回有效内容。"
                agent_observation.finish(
                    output=final_text,
                    metadata={
                        "model": model_name,
                        "duration_ms": duration_ms,
                        "turns": turns_used,
                        "tools": len(tool_events),
                        "needs_user": needs_user,
                    },
                    model=model_name if model_name != "-" else None,
                )
                return GenericAgentResult(
                    text=final_text,
                    model=model_name,
                    duration_ms=duration_ms,
                    turns=turns_used,
                    tool_events=tool_events,
                    needs_user=needs_user,
                )
            finally:
                self.observer.flush()

    def dispatch_tool(self, call: GenericToolCall) -> ToolExecution:
        """Execute one project-bounded tool call."""

        tool_name = call.name.strip()
        LOG.info("generic agent tool started | tool={}", tool_name)
        try:
            if tool_name == "project_tree":
                result = self._project_tree(call.arguments)
            elif tool_name == "file_read":
                result = self._file_read(call.arguments)
            elif tool_name == "ask_user":
                result = self._ask_user(call.arguments)
            elif tool_name == "finish":
                answer = str(call.arguments.get("answer") or call.arguments.get("content") or "").strip()
                result = ToolExecution("finish", "success", answer or "任务已完成。", should_exit=True)
            else:
                result = ToolExecution(tool_name or "unknown", "error", f"未知工具：{tool_name or '-'}")
        except Exception as exc:
            LOG.exception("generic agent tool failed | tool={} error={}", tool_name, exc)
            result = ToolExecution(tool_name or "unknown", "error", str(exc))
        LOG.info("generic agent tool finished | tool={} status={}", result.tool_name, result.status)
        return result

    def _build_prompt(self, user_content: str, tool_events: list[dict[str, str]]) -> str:
        tools = self.config.get("tools") or []
        context = "\n".join(f"- {event['tool']} [{event['status']}]: {event['content']}" for event in tool_events[-6:])
        template = str(self.config.get("prompt_template") or "{user_content}")
        return template.format(
            system_prompt=str(self.config.get("system_prompt") or ""),
            tool_protocol=str(self.config.get("tool_protocol") or ""),
            tools=json.dumps(tools, ensure_ascii=False, indent=2),
            project_root=self.project_root.as_posix(),
            tool_context=context or "暂无工具结果。",
            user_content=user_content,
        )

    def _continue_prompt(self, tool_results: list[str]) -> str:
        template = str(self.config.get("continue_prompt") or "{tool_results}")
        return template.format(tool_results="\n\n".join(tool_results))

    def _extract_tool_calls(self, text: str) -> tuple[str, list[GenericToolCall]]:
        calls: list[GenericToolCall] = []
        for match in TOOL_BLOCK_PATTERN.finditer(text):
            raw = match.group(1).strip().strip("`").strip()
            for payload in _as_payload_list(raw):
                name = str(payload.get("name") or payload.get("tool") or payload.get("function") or "").strip()
                args = payload.get("arguments") or payload.get("args") or payload.get("params") or {}
                if not isinstance(args, dict):
                    args = {"value": args}
                if name:
                    calls.append(GenericToolCall(name=name, arguments=dict(args), raw=raw))
        cleaned = TOOL_BLOCK_PATTERN.sub("", text).replace("```<tool_use>", "").replace("</tool_use>```", "").strip()
        return cleaned, calls

    def _project_tree(self, args: dict[str, Any]) -> ToolExecution:
        target, display = self._resolve_project_path(str(args.get("path") or args.get("relative_dir") or "."))
        if not target.exists():
            return ToolExecution("project_tree", "error", f"目录不存在：{display}")
        if target.is_file():
            target = target.parent
            display = target.relative_to(self.project_root).as_posix() or "."
        depth = _bounded_int(args.get("depth"), 1, 1, 3)
        limit = _bounded_int(args.get("limit"), 80, 5, 200)
        rows: list[str] = []
        self._collect_tree(target, depth=depth, limit=limit, rows=rows)
        content = f"项目目录：{display or '.'}\n" + "\n".join(rows[:limit])
        return ToolExecution("project_tree", "success", self._clip_text(content, self.max_tool_output_chars))

    def _collect_tree(self, target: Path, *, depth: int, limit: int, rows: list[str], prefix: str = "") -> None:
        if depth < 1 or len(rows) >= limit:
            return
        children = sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        for child in children:
            if len(rows) >= limit:
                return
            if child.name in self.ignored_names or child.name.startswith(".tmp"):
                continue
            rel = child.relative_to(self.project_root).as_posix()
            if child.is_dir():
                rows.append(f"{prefix}[DIR] {rel}")
                self._collect_tree(child, depth=depth - 1, limit=limit, rows=rows, prefix=prefix + "  ")
            elif self._is_text_file(child):
                rows.append(f"{prefix}[FILE] {rel}")

    def _file_read(self, args: dict[str, Any]) -> ToolExecution:
        target, display = self._resolve_project_path(str(args.get("path") or ""))
        if not target.exists() or not target.is_file():
            return ToolExecution("file_read", "error", f"文件不存在：{display}")
        if not self._is_text_file(target):
            return ToolExecution("file_read", "error", f"不支持读取非文本文件：{display}")
        start = _bounded_int(args.get("start"), 1, 1, 1_000_000)
        count = _bounded_int(args.get("count"), 200, 1, self.max_file_read_lines)
        keyword = str(args.get("keyword") or "").strip().lower()
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        start_index = start - 1
        if keyword:
            for index, line in enumerate(lines[start_index:], start=start_index):
                if keyword in line.lower():
                    start_index = max(0, index - max(1, count // 3))
                    break
        selected = lines[start_index : start_index + count]
        content_lines = [f"{start_index + offset + 1}|{line}" for offset, line in enumerate(selected)]
        header = f"[FILE] {display} lines={len(lines)} showing={len(selected)} start={start_index + 1}"
        return ToolExecution(
            "file_read",
            "success",
            self._clip_text("\n".join([header, *content_lines]), self.max_tool_output_chars),
        )

    def _ask_user(self, args: dict[str, Any]) -> ToolExecution:
        question = str(args.get("question") or "需要人工确认后继续。").strip()
        candidates = args.get("candidates") or []
        if isinstance(candidates, list) and candidates:
            question += "\n候选项：" + "；".join(str(item) for item in candidates)
        return ToolExecution("ask_user", "needs_user", question, should_exit=True, needs_user=True)

    def _resolve_project_path(self, relative_path: str) -> tuple[Path, str]:
        text = str(relative_path or "").strip() or "."
        target = (self.project_root / text).resolve()
        try:
            display = target.relative_to(self.project_root).as_posix()
        except ValueError as exc:
            raise ValueError("只能访问项目目录内的文件") from exc
        return target, display

    def _is_text_file(self, path: Path) -> bool:
        if path.name in {"README.md", ".env.example"}:
            return True
        return path.suffix.lower() in self.text_suffixes

    def _append_tool_trace(self, answer: str, tool_events: list[dict[str, str]]) -> str:
        lines = [answer.strip(), "", "---", "工具执行摘要："]
        for event in tool_events[-8:]:
            lines.append(f"- {event['tool']}：{event['status']}，{event['content'][:220]}")
        return "\n".join(line for line in lines if line is not None).strip()

    @staticmethod
    def _clip_text(value: str, limit: int) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        half = max(1, (limit - 40) // 2)
        return f"{text[:half]}\n...[内容过长已截断]...\n{text[-half:]}"

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        payload = data.get("generic_agent") if isinstance(data, dict) else {}
        return payload if isinstance(payload, dict) else {}


def _as_payload_list(raw: str) -> list[dict[str, Any]]:
    parsed = repair_json_loads(raw)
    if isinstance(parsed, list):
        return [dict(item) for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _bounded_int(value: Any, fallback: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = fallback
    return min(max(number, minimum), maximum)
