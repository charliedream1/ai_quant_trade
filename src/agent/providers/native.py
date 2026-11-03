"""Versioned noninteractive native protocols, without shell command construction."""

import re
import shutil
import subprocess
from pathlib import Path

from src.agent.qoder_cli import QoderCliRunner
from src.core.config import get_settings
from src.core.env_file import resolve_env_value
from src.core.process_env import process_environment
from src.strategy.codex_cli import CodexCliRunner, CodexStreamEvent

from .config import provider_config


def executable(backend: str) -> str | None:
    profile = provider_config()["providers"][backend]
    configured = resolve_env_value(profile["executable_env"])
    candidate = configured or next((path for name in profile["executables"] if (path := shutil.which(name))), None)
    if not candidate:
        return None
    path = Path(candidate)
    return str(path.resolve()) if path.is_file() else shutil.which(candidate)


def version(backend: str) -> str:
    path = executable(backend)
    if not path:
        return ""
    result = subprocess.run(
        [path, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=provider_config()["defaults"]["probe_timeout_seconds"],
        check=False,
    )
    if result.returncode:
        raise ValueError(f"{backend}版本检查失败（退出码{result.returncode}）")
    return result.stdout.strip()[:1000]


class NativeCliRunner(QoderCliRunner):
    """TRAE legacy/v2 and CodeBuddy share process lifecycle, not CLI arguments."""

    def __init__(self, backend: str, project_root: Path, timeout_seconds: float, protocol_version: str = ""):
        super().__init__(project_root, timeout_seconds)
        self.backend = backend
        self.display_name = provider_config()["providers"][backend]["label"]
        self.protocol = backend
        if backend == "trae":
            match = re.search(r"(?:version\s+|v)?(\d+)\.", protocol_version or version(backend))
            self.protocol = "trae_v2" if match and int(match[1]) >= 2 else "trae_legacy"

    def environment(self) -> dict[str, str]:
        env = process_environment(self.backend)
        profile = provider_config()["providers"][self.backend]
        if profile.get("native_config_env"):
            env[profile["native_config_env"]] = resolve_env_value(profile["config_dir_env"]) or str(
                get_settings().data_dir / "cli_profiles" / self.backend
            )
        env.update(profile.get("environment") or {})
        return env

    def command(self, prompt: str, *, model="", reasoning_effort="", image_paths=()) -> list[str]:
        path = executable(self.backend)
        if not path:
            raise ValueError(provider_config()["messages"]["missing"])
        profile = provider_config()["protocols"][self.protocol]
        if image_paths:
            raise ValueError("此生成协议不接收原生附件；请通过冻结证据提供内容")
        arguments = [path, *profile["arguments"]]
        for value, key in ((model, "model_flag"), (reasoning_effort, "effort_flag")):
            if value:
                if not profile[key]:
                    raise ValueError(f"{self.backend}当前协议未核验{key}，不能静默忽略选择")
                arguments.extend([profile[key], value])
        if prompt != "-" or self.protocol == "trae_v2":
            arguments.append(prompt)
        return arguments

    def stream(self, *args, **kwargs):
        self.partial = self.visible = ""
        yield from CodexCliRunner.stream(self, *args, **kwargs)

    def parse_events(self, value: dict):
        if self.protocol == "trae_v2":
            yield from CodexCliRunner.parse_events(self, value)
        else:
            yield from QoderCliRunner.parse_events(self, value)

    def parse_event(self, value: dict):
        if value.get("is_error") or value.get("type") == "error":
            return CodexStreamEvent(
                "error",
                "failed",
                str(value.get("error") or value.get("message") or value.get("result") or value),
                value,
            )
        event = (
            CodexCliRunner.parse_event(self, value)
            if self.protocol == "trae_v2"
            else QoderCliRunner.parse_event(self, value)
        )
        if event and event.kind == "process" and value.get("type") == "result":
            event.text = self.display_name + "已返回最终结果"
        return event


def runner_for(backend: str, directory: Path, timeout: float):
    if backend == "codex":
        return ProjectCodexRunner(directory, timeout)
    if backend == "qoder":
        return ResearchQoderRunner(directory, timeout)
    return NativeCliRunner(backend, directory, timeout)


class ProjectCodexRunner(CodexCliRunner):
    @staticmethod
    def executable() -> str | None:
        return executable("codex")


class ResearchQoderRunner(QoderCliRunner):
    """No native tools or configuration discovery in a platform research role."""

    enable_thinking: bool | None = None

    def command(self, prompt: str, *, model="", reasoning_effort="", image_paths=()) -> list[str]:
        if image_paths:
            raise ValueError("研究角色只接收冻结文本证据")
        command = super().command(prompt, model=model, reasoning_effort=reasoning_effort)
        for flag in ("--tools", "--setting-sources"):
            command[command.index(flag) + 1] = ""
        command.extend(["--system-prompt", provider_config()["prompts"]["system"]])
        if getattr(self, "enable_thinking", None) is not None:
            command.extend(["--thinking", "enabled" if self.enable_thinking else "disabled"])
        return command

    def environment(self):
        env = super().environment()
        env["ALL_IN_ONE_PROVIDER_DEPTH"] = str(provider_config()["defaults"]["max_provider_depth"])
        return env

    def parse_events(self, value: dict):
        # Every transport record must reach the research guard, including records
        # that ordinary conversation rendering deliberately ignores.
        yield CodexStreamEvent("event", "running", "", value)
        yield from super().parse_events(value)
