"""Assistant frontend service callbacks."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from html import escape
from time import perf_counter
from typing import cast

from src.agent.composer_config import normalize_backend
from src.agent.providers.config import provider_config
from src.agent.providers.native import NativeCliRunner
from src.agent.qoder_cli import QoderCliRunner
from src.agent.rag import RAGService
from src.agent.real_models import real_model, real_profile, require_real_model
from src.core.assistant_page_context import context_identity, context_prompt
from src.core.panel_updates import observe_references
from src.core.repository import Repository
from src.core.stream_control import stream_cancelled
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

    def floating_models(self):
        rows = Repository().db.query("SELECT * FROM llm_models WHERE enabled=1 ORDER BY is_default DESC,id DESC")
        return [(str(row["name"] or row["model_name"]), row["model_name"]) for row in rows if real_profile(row)]

    def floating_send(self, session, message, history, backend, attachments, model, effort, access):
        if normalize_backend(backend) == "generic_agent":
            model = real_model(str(model or ""))["model_name"]
        with require_real_model():
            yield from cast(Any, self).ai_console_send_stream(
                session, message, history, backend, attachments, model, effort, access
            )

    def floating_qa(self, question, category, top_k, page_context=None):
        selected = real_model()
        from .foundation import to_frame

        with (
            require_real_model(),
            observe_references(1, lambda refs: to_frame(refs, ["citation", "title", "snippet", "doc_id", "chunk_id"])),
        ):
            result = RAGService().ask(
                {
                    "question": require_text(question, "Question"),
                    "category_id": category or None,
                    "top_k": int(top_k),
                    "model_id": selected["id"],
                    "page_context": page_context,
                    "session_id": "floating-" + context_identity(page_context)[:40] if page_context else "default",
                }
            )

        return result.get("answer") or "", to_frame(
            result.get("references") or [], ["citation", "title", "snippet", "doc_id", "chunk_id"]
        )

    def floating_citation(self, rows, index):
        from src.documents.service import FilePreviewService
        from src.documents.view import launcher

        row = rows.iloc[int(index)].to_dict()
        text = row.get("chunk_content") or row.get("snippet") or row.get("content") or ""
        if row.get("chunk_id"):
            chunk = Repository().db.query_one(
                "SELECT content FROM kb_document_chunks WHERE id=?", (int(row["chunk_id"]),)
            )
            if chunk:
                text = chunk["content"]
        original = launcher(FilePreviewService().knowledge(int(row["doc_id"]))) if row.get("doc_id") else ""
        original = re.sub(r' data-preview-auto="[^"]*"', "", original)
        return f"<h4>{escape(str(row.get('title') or 'Source'))}</h4><pre class='citation-full'>{escape(str(text))}</pre>{original}"

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
    prompt = (
        json.dumps({"history": history, "message": question}, ensure_ascii=False) if history else question
    ) + context_prompt()
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
    for event in runner.stream(prompt, stdin_prompt=True, cancelled=stream_cancelled):
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
