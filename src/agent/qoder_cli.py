"""Qoder headless adapter using public message events and explicit tool permissions."""

import json
import shutil
import subprocess
from pathlib import Path
from time import monotonic

from json_repair import loads as repair_json

from src.core.config import get_settings
from src.core.env_file import resolve_env_value
from src.core.process_env import process_environment
from src.strategy.codex_cli import CodexCliRunner, CodexStreamEvent

from .composer_config import composer_config

MODEL_CACHE: dict[str, tuple[float, list[tuple[str, str]], str]] = {}
AUTH_CACHE: dict[str, tuple[float, dict]] = {}


class QoderCliRunner(CodexCliRunner):
    display_name = "Qoder CLI"

    def __init__(self, project_root=None, timeout_seconds=None, *, access_mode="read-only"):
        self.config = composer_config()["qoder"]
        super().__init__(project_root, timeout_seconds or self.config["timeout_seconds"], access_mode=access_mode)
        self.partial = ""
        self.visible = ""

    @staticmethod
    def executable() -> str | None:
        cfg = composer_config()["qoder"]
        return resolve_env_value(cfg["executable_env"]) or next(
            (value for name in cfg["executables"] if (value := shutil.which(name))), None
        )

    def environment(self) -> dict[str, str]:
        env = process_environment("qoder")
        env["QODER_CONFIG_DIR"] = resolve_env_value(self.config["config_dir_env"]) or str(
            get_settings().data_dir / "qoder"
        )
        return env

    def command(self, prompt: str, *, model="", reasoning_effort="", image_paths=()) -> list[str]:
        executable = self.executable()
        if not executable or not Path(executable).is_file() and not shutil.which(executable):
            raise RuntimeError(self.config["missing"])
        command = [
            executable,
            "--output-format",
            "stream-json",
            "--no-session-persistence",
            "--cwd",
            str(self.project_root),
            "--permission-mode",
            self.config["permission_modes"][self.access_mode],
            "--tools",
            ",".join(self.config["tools"][self.access_mode]),
            "--disallowed-tools",
            ",".join(self.config["disabled_tools"]),
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--setting-sources",
            "user",
            "--settings",
            json.dumps(self.config["settings"]),
            "--max-model-request-retries",
            "0",
            "--max-output-tokens",
            str(self.config["max_output_tokens"]),
        ]
        if model.strip():
            command += ["--model", model.strip()]
        if reasoning_effort.strip():
            command += ["--reasoning-effort", reasoning_effort.strip()]
        for image in image_paths:
            command += ["--attachment", str(Path(image).resolve())]
        command += ["--print"]
        if prompt != "-":
            command.append(prompt)
        return command

    def stream(self, *args, **kwargs):
        yield CodexStreamEvent("process", "checking-auth", "检查Qoder登录状态；尚未启动模型对话")
        state = authentication_status(self)
        if state.get("logged_in") is not True:
            message = self.config["login_required"] if state.get("logged_in") is False else self.config["status_failed"]
            yield CodexStreamEvent("error", "unavailable", message)
            return
        self.partial = self.visible = ""
        yield from super().stream(*args, **kwargs)

    def parse_event(self, value: dict) -> CodexStreamEvent | None:
        kind = value.get("type", "")
        if kind == "stream_event":
            event = value.get("event") or {}
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                text = str(delta.get("text") or "")
                self.partial += text
                self.visible += text
                return CodexStreamEvent("message", "running", text, value)
        if kind == "assistant":
            content = (value.get("message") or {}).get("content") or []
            text = "".join(str(row.get("text") or "") for row in content if row.get("type") == "text")
            if text:
                suffix = text[len(self.partial) :] if self.partial and text.startswith(self.partial) else text
                self.partial = ""
                if suffix:
                    self.visible += suffix
                    return CodexStreamEvent("message", "running", suffix, value)
            tools = [row for row in content if row.get("type") == "tool_use"]
            if tools:
                return CodexStreamEvent("action", "running", json.dumps(tools, ensure_ascii=False), value)
        if kind == "result":
            text = str(value.get("result") or "")
            if value.get("is_error") or str(value.get("subtype", "")).startswith("error"):
                return CodexStreamEvent("error", "failed", text or str(value.get("errors") or value), value)
            if not self.visible and text:
                self.visible = text
                return CodexStreamEvent("message", "completed", text, value)
            return CodexStreamEvent("process", "completed", "Qoder已返回最终结果", value)
        if kind in {"system", "user"}:
            return CodexStreamEvent("process", "running", json.dumps(value, ensure_ascii=False), value)
        if kind == "error":
            return CodexStreamEvent("error", "failed", str(value.get("error") or value.get("message") or value), value)
        return None

    def parse_events(self, value: dict):
        event = self.parse_event(value)
        if event:
            yield event
        if value.get("type") == "assistant" and event and event.kind == "message":
            tools = [row for row in (value.get("message") or {}).get("content", []) if row.get("type") == "tool_use"]
            if tools:
                yield CodexStreamEvent("action", "running", json.dumps(tools, ensure_ascii=False), value)


def authentication_status(runner: QoderCliRunner, refresh=False) -> dict:
    executable = runner.executable()
    key = str(executable) + runner.environment()["QODER_CONFIG_DIR"]
    cached = AUTH_CACHE.get(key)
    if cached and not refresh and monotonic() - cached[0] < runner.config["auth_cache_seconds"]:
        return cached[1]
    state = {}
    if executable:
        try:
            result = subprocess.run(
                [executable, "--setting-sources", "user", "status", "--output", "json"],
                cwd=runner.project_root,
                env=runner.environment(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=runner.config["metadata_timeout_seconds"],
            )
            value = repair_json(result.stdout)
            if result.returncode == 0 and isinstance(value, dict):
                state = {key: value[key] for key in ("logged_in", "version") if key in value}
        except (OSError, subprocess.TimeoutExpired, ValueError):
            state = {}
    AUTH_CACHE[key] = (monotonic(), state)
    return state


def model_choices(refresh=False) -> tuple[list[tuple[str, str]], str]:
    runner = QoderCliRunner()
    executable = runner.executable()
    cfg = runner.config
    key = str(executable) + runner.environment()["QODER_CONFIG_DIR"]
    cached = MODEL_CACHE.get(key)
    if cached and not refresh and monotonic() - cached[0] < cfg["model_cache_seconds"]:
        return cached[1], cached[2]
    choices = [("默认模型", "")]
    note = cfg["missing"] if not executable else cfg["no_models"]
    if refresh and executable:
        state = authentication_status(runner, refresh=True)
        if state.get("logged_in") is not True:
            return choices, cfg["login_required"] if state.get("logged_in") is False else cfg["status_failed"]
        try:
            result = subprocess.run(
                [executable, "--setting-sources", "user", "--list-models"],
                cwd=runner.project_root,
                env=runner.environment(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=cfg["metadata_timeout_seconds"],
            )
            value = repair_json(result.stdout)
            rows = value.get("models", []) if isinstance(value, dict) else value if isinstance(value, list) else []
            for row in rows:
                if isinstance(row, dict) and (identifier := row.get("id") or row.get("model") or row.get("name")):
                    choices.append((str(row.get("name") or identifier), str(identifier)))
            note = "已读取Qoder账户模型；也可输入CLI支持的模型标识" if len(choices) > 1 else cfg["no_models"]
        except (OSError, subprocess.TimeoutExpired, ValueError):
            note = cfg["no_models"]
    MODEL_CACHE[key] = (monotonic(), choices, note)
    return choices, note
