"""Shared AI execution for UI and API, with observable native provider events."""

import json
import os
from typing import Any
from uuid import uuid4

from src.agent.attachments import AttachmentBundle
from src.agent.generic_agent_runtime import GenericAgentRuntime
from src.agent.providers.native import NativeCliRunner
from src.core.assistant_page_context import context_prompt
from src.core.config import get_settings
from src.core.redaction import redact_text
from src.core.repository import Repository
from src.core.stream_control import stream_cancelled
from src.observability.instrumentation import traced
from src.observability.runtime import current_observation
from src.strategy.codex_cli import CodexCliRunner

from .composer_config import composer_config, validate_selection
from .qoder_cli import QoderCliRunner


def backend_events(repo: Repository, payload: dict[str, Any], history: list[dict[str, str]], bundle: AttachmentBundle):
    payload = validate_selection(payload)
    backend = str(payload.get("backend") or "generic").lower().replace("-", "_")
    if backend in {"generic", "generic_agent", "model", "model_api", "openai"}:
        result = GenericAgentRuntime(repo=repo).run_once(
            str(payload["message"]) + bundle.text_context + context_prompt(),
            history=history,
            session_id=payload.get("session_id"),
            model_id=payload.get("model_id"),
            reasoning_effort=payload.get("reasoning_effort"),
            image_paths=bundle.image_data_urls(),
        )
        for tool_event in result.tool_events:
            yield {"type": "action", "data": tool_event}
        yield {"type": "message", "data": {"text": result.text}}
        yield {
            "type": "backend_result",
            "data": {
                "text": result.text,
                "model": result.model,
                "status": "mock"
                if "mock" in result.model.lower()
                else "needs_user"
                if result.needs_user
                else "completed",
                "duration_ms": result.duration_ms,
                "turns": result.turns,
                "tool_events": result.tool_events,
            },
        }
        return
    if backend not in {"codex", "codex_cli", "qoder", "trae", "codebuddy", "workbuddy"}:
        yield {
            "type": "backend_result",
            "data": {"text": f"{backend} 未接入真实对话", "status": "unavailable", "backend": backend},
        }
        return
    if get_settings().data_mode == "mock" and os.environ.get("ALL_IN_ONE_ENABLE_REAL_CLI", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        yield {
            "type": "backend_result",
            "data": {
                "text": f"mock 模式未执行真实 {composer_config()['backends'][backend]['label']}，请切换 real 模式并显式启用 CLI",
                "status": "mock-disabled",
                "backend": backend,
            },
        }
        return
    if backend == "workbuddy":
        yield from _workbuddy_events(payload, history, bundle)
        return
    text = ""
    error = ""
    status = "running"
    prompt = str(payload["message"]) + bundle.text_context + context_prompt()
    if history:
        prompt = json.dumps({"history": history, "message": prompt}, ensure_ascii=False)
    runner: CodexCliRunner
    if backend in {"trae", "codebuddy"}:
        runner = NativeCliRunner(backend, get_settings().project_root, composer_config()["qoder"]["timeout_seconds"])
    else:
        runner_type = QoderCliRunner if backend == "qoder" else CodexCliRunner
        runner = runner_type(access_mode=payload.get("access_mode", "read-only"))
    for event in runner.stream(
        prompt,
        model=str(payload.get("model_name") or ""),
        reasoning_effort=str(payload.get("reasoning_effort") or ""),
        image_paths=bundle.cli_image_paths(),
        stdin_prompt=True,
        cancelled=stream_cancelled,
    ):
        if event.kind == "message":
            text += event.text
        if event.kind == "error":
            error = event.text
        status = event.status
        yield {"type": event.kind, "data": {"text": event.text, "status": status, "raw": event.raw}}
    if not text and not error:
        error = "CLI没有返回可见正文"
    yield {
        "type": "backend_result",
        "data": {
            "text": text or error,
            "status": "failed" if error else status,
            "backend": backend,
            "model": str(payload.get("model_name") or backend + "-default"),
            "access_mode": payload.get("access_mode", "read-only"),
            "is_mock": False,
            "error": error,
        },
    }


def _workbuddy_events(payload, history, bundle):
    cfg = composer_config()["workbuddy_chat"]
    name = str(payload.get("model_name") or "")
    if not name or bundle.image_paths:
        message = cfg["images"] if bundle.image_paths else cfg["select_model"]
        yield {"type": "backend_result", "data": {"text": message, "status": "failed", "backend": "workbuddy"}}
        return
    prompt = str(payload["message"]) + bundle.text_context + context_prompt()
    if history:
        kept, length = [], 0
        for turn in reversed(history):
            length += len(turn["content"])
            if length > cfg["max_history_chars"]:
                break
            kept.append(turn)
        prompt = json.dumps({"history": list(reversed(kept)), "message": prompt}, ensure_ascii=False)
    if len(prompt) > cfg["max_prompt_chars"]:
        yield {
            "type": "backend_result",
            "data": {"text": cfg["prompt_limit"], "status": "failed", "backend": "workbuddy"},
        }
        return
    yield {"type": "process", "data": {"text": cfg["started"], "status": "running"}}
    try:
        result = _workbuddy_turn(prompt, name, cfg)
    except (OSError, ValueError, TimeoutError) as exc:
        message = redact_text(str(exc)) if isinstance(exc, ValueError) else "WorkBuddy CLI 调用中断或超时。"
        yield {"type": "backend_result", "data": {"text": message, "status": "failed", "backend": "workbuddy"}}
        return
    text = result["text"]
    yield {"type": "message", "data": {"text": text, "status": "running"}}
    yield {"type": "process", "data": {"text": cfg["finished"], "status": "completed"}}
    yield {
        "type": "backend_result",
        "data": {
            **result,
            "status": "completed",
            "access_mode": "read-only",
            "is_mock": False,
        },
    }


@traced("llm.workbuddy_chat", "generation")
def _workbuddy_turn(prompt, name, cfg):
    from src.engine.market.model_graph.generation import complete_workbuddy

    directory = get_settings().data_dir / cfg["directory"] / uuid4().hex
    result = complete_workbuddy(
        prompt, model=name, directory=directory, cancelled=stream_cancelled, system_prompt=cfg["system"]
    )
    current_observation().finish(model=result["model"], usage=result["usage"])
    return result
