"""Assistant frontend service callbacks."""

from __future__ import annotations

import re
from collections.abc import Iterator
from html import escape
from time import perf_counter
from typing import cast

from src.agent.attachments import AttachmentBundle
from src.agent.composer_config import composer_config, normalize_backend
from src.agent.rag import RAGService
from src.agent.real_models import real_model, real_profile, require_real_model
from src.agent.workspace_backend import backend_events
from src.core.assistant_page_context import context_identity
from src.core.panel_updates import observe_references
from src.core.repository import Repository

from .foundation import (
    Any,
    LLMClient,
    _chat_history_messages,
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
        *,
        model_name: str = "",
        reasoning_effort: str = "",
        access_mode: str = "read-only",
    ) -> Iterator[tuple[list[dict[str, str]], str, str]]:
        question = require_text(message, "CLI 消息")
        messages = _chat_history_messages(history)
        provider = normalize_backend(cli_type or "codex")
        if provider == "generic_agent":
            raise ValueError("请选择 CLI 后端")
        yield from _cli_chat_events(question, messages, provider, model_name, reasoning_effort, access_mode)


def _cli_chat_events(
    question: str,
    history: list[dict[str, str]],
    provider: str,
    model_name: str,
    reasoning_effort: str,
    access_mode: str,
) -> Iterator[tuple[list[dict[str, str]], str, str]]:
    started = perf_counter()
    shown = history + [{"role": "user", "content": question}]
    yield shown, "", "已接收 CLI 消息"
    profiles = composer_config()["backends"]
    label = profiles.get(provider, {}).get("label", provider)
    text = ""
    request = {
        "message": question,
        "backend": provider,
        "model_name": model_name,
        "reasoning_effort": reasoning_effort,
        "access_mode": access_mode,
    }
    for event in backend_events(Repository(), request, history, AttachmentBundle()):
        data = event["data"]
        if event["type"] == "backend_result":
            answer = data.get("text") or text
            outcome = data["status"]
            duration = round((perf_counter() - started) * 1000)
            yield shown + [{"role": "assistant", "content": answer}], "", f"{label} {outcome} · {duration} ms"
            return
        if event["type"] == "message":
            text += str(data.get("text") or "")
        messages = shown + ([{"role": "assistant", "content": text}] if text else [])
        yield messages, "", f"{label} {data.get('status', 'running')}"
