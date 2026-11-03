"""Safe, observable adapter for a local Codex CLI conversation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from src.core.config import PROJECT_ROOT
from src.core.logger import get_logger
from src.core.process_env import process_environment

LOG = get_logger("strategy.codex_cli")
STDERR_TAIL_LINES = 100
CANCELLATION_POLL_SECONDS = 0.25


@dataclass(slots=True)
class CodexStreamEvent:
    """One observable event emitted by ``codex exec --json``."""

    kind: str
    status: str
    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CodexRunResult:
    """Final Codex response and execution evidence."""

    status: str
    text: str
    events: list[dict[str, Any]]
    command: list[str]
    duration_ms: int
    error: str = ""


class CodexCliRunner:
    """Run Codex in read-only non-interactive mode and preserve event evidence."""

    display_name = "Codex CLI"

    def __init__(
        self, project_root: Path | None = None, timeout_seconds: float | None = None, *, access_mode: str = "read-only"
    ) -> None:
        self.project_root = (project_root or PROJECT_ROOT).resolve()
        if access_mode not in {"read-only", "workspace-write"}:
            raise ValueError("不支持的CLI访问权限")
        self.access_mode = access_mode
        configured = (
            timeout_seconds
            if timeout_seconds is not None
            else os.environ.get("ALL_IN_ONE_CODEX_TIMEOUT_SECONDS", 180.0)
        )
        self.timeout_seconds = max(float(configured), 3.0)

    @staticmethod
    def executable() -> str | None:
        configured = str(os.environ.get("ALL_IN_ONE_CODEX_CLI", "")).strip()
        return configured or shutil.which("codex")

    def command(
        self,
        prompt: str,
        *,
        model: str = "",
        reasoning_effort: str = "",
        image_paths: Sequence[str | Path] = (),
    ) -> list[str]:
        executable = self.executable()
        if not executable:
            raise RuntimeError("未找到 Codex CLI，请配置 ALL_IN_ONE_CODEX_CLI 或将 codex 加入 PATH")
        command = [
            executable,
            "exec",
            "--json",
            "--ephemeral",
            "--sandbox",
            self.access_mode,
            "--skip-git-repo-check",
            "--cd",
            str(self.project_root),
        ]
        if model.strip():
            command.extend(["--model", model.strip()])
        if reasoning_effort.strip():
            command.extend(["--config", f"model_reasoning_effort={reasoning_effort.strip()}"])
        for image_path in image_paths:
            command.extend(["--image", str(Path(image_path).resolve())])
        command.append(prompt)
        return command

    def stream(
        self,
        prompt: str,
        *,
        model: str = "",
        reasoning_effort: str = "",
        image_paths: Sequence[str | Path] = (),
        stdin_prompt: bool = False,
        cancelled: Callable[[], bool] | None = None,
    ) -> Iterator[CodexStreamEvent]:
        command = self.command(
            "-" if stdin_prompt else prompt,
            model=model,
            reasoning_effort=reasoning_effort,
            image_paths=image_paths,
        )
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=str(self.project_root),
            stdin=subprocess.PIPE if stdin_prompt else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.environment(),
        )
        LOG.info(
            "{} started | pid={} model={} images={}",
            self.display_name,
            process.pid,
            model or "default",
            len(image_paths),
        )
        timed_out = threading.Event()
        stderr_lines: deque[str] = deque(maxlen=STDERR_TAIL_LINES)

        def stop_timeout() -> None:
            if process.poll() is None:
                timed_out.set()
                process.kill()

        def drain_stderr() -> None:
            if process.stderr is not None:
                stderr_lines.extend(process.stderr)

        def feed_prompt() -> None:
            if process.stdin is not None:
                try:
                    process.stdin.write(prompt)
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass  # The normal exit-code/stderr path reports early process exits.

        # A silent stdout must still time out; drain stderr so its pipe cannot block the child.
        timeout = threading.Timer(self.timeout_seconds, stop_timeout)
        timeout.daemon = True
        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stderr_thread.start()
        timeout.start()
        input_thread = threading.Thread(target=feed_prompt, daemon=True)
        watcher_stop = threading.Event()

        def watch_cancel() -> None:
            while not watcher_stop.wait(CANCELLATION_POLL_SECONDS):
                if cancelled and cancelled():
                    if process.poll() is None:
                        process.kill()
                    return

        cancel_thread = threading.Thread(target=watch_cancel, daemon=True)
        if cancelled:
            cancel_thread.start()
        if stdin_prompt:
            input_thread.start()
        try:
            yield CodexStreamEvent("process", "running", f"{self.display_name} 已启动 · {self.access_mode}")
            if process.stdout is None:
                raise RuntimeError("Codex CLI stdout 管道不可用")
            for line in process.stdout:
                if time.monotonic() - started > self.timeout_seconds:
                    process.kill()
                    yield CodexStreamEvent("error", "timeout", f"{self.display_name} 执行超时")
                    return
                parsed = _parse_json_line(line)
                if parsed is None:
                    continue
                yield from self.parse_events(parsed)
            return_code = process.wait(timeout=5)
            stderr_thread.join(timeout=1)
            if timed_out.is_set():
                yield CodexStreamEvent("error", "timeout", f"{self.display_name} 执行超时")
            elif return_code != 0:
                stderr = "".join(stderr_lines)
                detail = stderr.strip()[-1000:] or f"{self.display_name} 退出码 {return_code}"
                yield CodexStreamEvent("error", "failed", detail)
            else:
                yield CodexStreamEvent("process", "completed", f"{self.display_name} 已完成")
        except subprocess.TimeoutExpired:
            process.kill()
            yield CodexStreamEvent("error", "timeout", f"{self.display_name} 进程未在超时前结束")
        finally:
            watcher_stop.set()
            if cancelled:
                cancel_thread.join(timeout=1)
            timeout.cancel()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            stderr_thread.join(timeout=1)
            if stdin_prompt:
                input_thread.join(timeout=1)
            for pipe in (process.stdout, process.stderr):
                if pipe is not None:
                    pipe.close()
            LOG.info(
                "{} finished | pid={} duration_ms={} returncode={}",
                self.display_name,
                process.pid,
                round((time.monotonic() - started) * 1000),
                process.returncode,
            )

    def environment(self) -> dict[str, str]:
        return process_environment("codex")

    def parse_event(self, value: dict[str, Any]) -> CodexStreamEvent | None:
        return _event_from_json(value)

    def parse_events(self, value: dict[str, Any]) -> Iterator[CodexStreamEvent]:
        event = self.parse_event(value)
        if event:
            yield event

    def run_once(
        self,
        prompt: str,
        *,
        model: str = "",
        reasoning_effort: str = "",
        image_paths: Sequence[str | Path] = (),
    ) -> CodexRunResult:
        command = self.command(prompt, model=model, reasoning_effort=reasoning_effort, image_paths=image_paths)
        events: list[dict[str, Any]] = []
        text_parts: list[str] = []
        status = "running"
        error = ""
        started = time.monotonic()
        for event in self.stream(prompt, model=model, reasoning_effort=reasoning_effort, image_paths=image_paths):
            events.append({"kind": event.kind, "status": event.status, "text": event.text, "raw": event.raw})
            status = event.status
            if event.text and event.kind == "message":
                text_parts.append(event.text)
            if event.kind == "error":
                error = event.text
        return CodexRunResult(
            status="failed" if error else ("completed" if status == "completed" else status),
            text="\n".join(part for part in text_parts if part).strip(),
            events=events,
            command=command,
            duration_ms=round((time.monotonic() - started) * 1000),
            error=error,
        )


def _parse_json_line(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _event_from_json(payload: dict[str, Any]) -> CodexStreamEvent | None:
    event_type = str(payload.get("type") or "")
    item = cast(dict[str, Any], payload.get("item") if isinstance(payload.get("item"), dict) else {})
    item_type = str(item.get("type") or "")
    if item_type == "agent_message":
        return CodexStreamEvent("message", "running", str(item.get("text") or ""), payload)
    if event_type == "turn.started":
        return CodexStreamEvent("turn", "running", "Codex 正在思考", payload)
    if event_type == "turn.completed":
        return CodexStreamEvent("turn", "completed", "Codex 回合已完成", payload)
    if item_type in {"command_execution", "mcp_tool_call", "file_change"}:
        return CodexStreamEvent("action", "running", _action_text(item_type, item), payload)
    if item_type == "error" or event_type == "error":
        message = str(item.get("message") or payload.get("message") or "Codex CLI 返回错误")
        if "ignoring" in message.lower() or "warning" in message.lower():
            return CodexStreamEvent("warning", "running", message, payload)
        return CodexStreamEvent("error", "failed", message, payload)
    return CodexStreamEvent("event", "running", "", payload)


def _action_text(item_type: str, item: dict[str, Any]) -> str:
    if item_type == "command_execution":
        return f"执行命令：{str(item.get('command') or '')[:160]}"
    if item_type == "file_change":
        return "处理文件变更（当前为只读模式）"
    return "调用工具"
