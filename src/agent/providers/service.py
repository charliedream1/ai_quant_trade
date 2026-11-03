"""Common ordinary-text generation. Domain agents retain their own ReAct and gates."""

import json
import os
from time import perf_counter
from uuid import uuid4

from src.agent.llm_client import LLMClient
from src.core.config import get_settings

from .config import provider_config
from .events import collect_response
from .native import runner_for
from .registry import check_identity, provider_snapshot, require_native


class ProviderClient:
    def __init__(self, llm=None):
        self.llm = llm

    def complete(
        self,
        prompt: str,
        *,
        selection: dict | None = None,
        expected_provider=None,
        emit=None,
        cancelled=None,
        timeout_seconds=None,
        max_output_chars=None,
        **options,
    ) -> dict:
        cfg = provider_config()
        selected = dict(selection or {})
        backend = selected.get("backend") or cfg["defaults"]["backend"]
        if backend not in cfg["providers"]:
            raise ValueError(cfg["messages"]["unknown"])
        if cancelled and cancelled():
            raise ValueError(cfg["messages"]["cancelled"])
        if backend == "api":
            request = {
                **options,
                **{
                    key: selected[key]
                    for key in ("model_id", "reasoning_effort", "enable_thinking")
                    if selected.get(key) is not None
                },
            }
            llm = self.llm or LLMClient()
            try:
                started = perf_counter()
                if timeout_seconds is not None:
                    request["timeout_seconds"] = timeout_seconds
                if max_output_chars is not None:
                    request["max_output_chars"] = max_output_chars
                if expected_provider:
                    check_identity(expected_provider, provider_snapshot(selected, client=llm))
                result = llm.complete(prompt, **request)
                if timeout_seconds is not None and perf_counter() - started > timeout_seconds:
                    raise TimeoutError("模型调用超过本轮截止时间")
                if max_output_chars is not None and len(str(result.get("text") or "")) > max_output_chars:
                    raise ValueError("模型正文超过本轮输出预算")
                if cancelled and cancelled():
                    raise ValueError(cfg["messages"]["cancelled"])
                return {**result, "backend": "api", "usage": result.get("usage") or None}
            finally:
                if self.llm is None:
                    llm.session.close()
        return self._native(
            prompt, selected, options, emit, cancelled, expected_provider, timeout_seconds, max_output_chars
        )

    def _native(self, prompt, selected, options, emit, cancelled, expected, timeout, output_limit):
        cfg = provider_config()
        if int(os.environ.get("ALL_IN_ONE_PROVIDER_DEPTH", "0")) >= cfg["defaults"]["max_provider_depth"]:
            raise ValueError(cfg["messages"]["recursive"])
        state = require_native(selected)
        check_identity(expected, state)
        directory = get_settings().data_dir / "provider_calls" / uuid4().hex
        if not directory.resolve().is_relative_to(get_settings().project_root.resolve()):
            raise ValueError("生成证据目录必须位于本项目内")
        directory.mkdir(parents=True, exist_ok=False)
        context = {
            "system": cfg["prompts"]["system"],
            "history": options.get("history") or [],
            "prompt": prompt,
        }
        frozen = json.dumps(context, ensure_ascii=False)
        (directory / "request.json").write_text(frozen, encoding="utf-8")
        if emit:
            emit(
                "provider_request",
                "已冻结CLI调用上下文；尚未产生模型回复",
                {
                    "artifact_dir": str(directory),
                    "provider": state,
                    "purpose": options.get("purpose"),
                },
            )
        timeout = min(timeout or cfg["defaults"]["timeout_seconds"], cfg["defaults"]["timeout_seconds"])
        runner = runner_for(state["backend"], directory, timeout)
        if state["backend"] == "qoder":
            runner.enable_thinking = selected.get("enable_thinking", options.get("enable_thinking"))
        if hasattr(runner, "config"):
            runner.config = {
                **runner.config,
                "max_output_tokens": min(
                    options.get("max_output_tokens") or cfg["defaults"]["max_output_tokens"],
                    cfg["defaults"]["max_output_tokens"],
                ),
            }
        started = perf_counter()
        events: list[dict] = []
        iterator = runner.stream(
            frozen,
            model=selected.get("model_name") or "",
            reasoning_effort=selected.get("reasoning_effort") or "",
            stdin_prompt=True,
            cancelled=cancelled,
        )
        try:
            result = collect_response(
                iterator,
                state["backend"],
                cfg,
                emit,
                cancelled,
                min(output_limit or cfg["defaults"]["max_output_chars"], cfg["defaults"]["max_output_chars"]),
                events,
            )
            return {
                **result,
                "model": result["model"] or selected.get("model_name") or state["backend"] + ":default-unreported",
                "backend": state["backend"],
                "provider": state,
                "duration_ms": round((perf_counter() - started) * 1000),
                "artifact_dir": str(directory),
            }
        finally:
            iterator.close()
            (directory / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
            (directory / "provider.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
