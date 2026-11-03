"""Assistant frontend service callbacks."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from time import perf_counter

from src.agent.composer_config import normalize_backend
from src.agent.providers.config import provider_config
from src.agent.providers.native import NativeCliRunner
from src.agent.qoder_cli import QoderCliRunner
from src.strategy.codex_cli import CodexCliRunner

from .foundation import (
    CLI_PROVIDERS,
    Any,
    LLMClient,
    _chat_history_messages,
    get_settings,
    require_text,
)


class AssistantServiceMixin:
    """Callbacks owned by the assistant frontend domain."""

    def floating_chat(
        self,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
    ) -> tuple[list[dict[str, str]], str, str]:
        question = require_text(message, "问题")
        messages = _chat_history_messages(history)
        context: list[dict[str, str]] = []
        context.extend(messages)
        result = LLMClient().complete(question, purpose="悬浮问答", history=context)
        messages.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": result["text"]},
            ]
        )
        status = f"`{result['model']}` · {result['duration_ms']} ms"
        return messages, "", status

    def floating_cli_chat(
        self,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
        cli_type: str,
    ) -> tuple[list[dict[str, str]], str, str]:
        return list(self.floating_cli_chat_stream(message, history, cli_type))[-1]

    def floating_cli_chat_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | list[list[str | None]] | None,
        cli_type: str,
    ) -> Iterator[tuple[list[dict[str, str]], str, str]]:
        question = require_text(message, "CLI 消息")
        messages = _chat_history_messages(history)
        provider = normalize_backend(cli_type or "codex")
        if provider not in {"codex", "qoder", "trae", "codebuddy"}:
            answer = f"{CLI_PROVIDERS.get(provider, provider)} 未接入真实对话，未生成模拟日志。"
        elif str(get_settings().data_mode).lower() == "mock" and str(
            os.environ.get("ALL_IN_ONE_ENABLE_REAL_CLI", "")
        ).lower() not in {"1", "true", "yes"}:
            answer = f"mock 模式未执行真实 {provider} CLI，请切换 real 模式并显式启用 CLI。"
        else:
            yield from _codex_chat_events(question, messages, provider)
            return
        messages.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
        yield messages, "", answer


def _codex_chat_events(
    question: str, history: list[dict[str, str]], provider: str = "codex"
) -> Iterator[tuple[list[dict[str, str]], str, str]]:
    started = perf_counter()
    shown = history + [{"role": "user", "content": question}]
    yield shown, "", "已接收 CLI 消息"
    prompt = json.dumps({"history": history, "message": question}, ensure_ascii=False) if history else question
    text = ""
    error = ""
    status = "running"
    runner = (
        NativeCliRunner(provider, get_settings().project_root, provider_config()["defaults"]["timeout_seconds"])
        if provider in {"trae", "codebuddy"}
        else QoderCliRunner()
        if provider == "qoder"
        else CodexCliRunner()
    )
    for event in runner.stream(prompt, stdin_prompt=True):
        if event.kind == "message":
            text += event.text
        if event.kind == "error":
            error = event.text
        status = event.status
        messages = shown + ([{"role": "assistant", "content": text or error}] if text or error else [])
        yield messages, "", f"{runner.display_name} {status} · {event.text}"
    answer = text or (f"{runner.display_name} 调用失败：{error}" if error else f"{runner.display_name} 未返回正文。")
    final_status = "failed" if error or not text else status
    yield (
        shown + [{"role": "assistant", "content": answer}],
        "",
        f"{runner.display_name} {final_status} · {round((perf_counter() - started) * 1000)} ms",
    )
