"""Optional Langfuse observations for the GenericAgent runtime."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.env_file import resolve_env_value
from src.core.logger import get_logger

LOG = get_logger("agent.langfuse")
ENV_ENABLED = "ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENABLED"
ENV_CAPTURE_CONTENT = "ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_CAPTURE_CONTENT"
ENV_FLUSH_ON_FINISH = "ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_FLUSH_ON_FINISH"
ENV_ENVIRONMENT = "ALL_IN_ONE_GENERIC_AGENT_LANGFUSE_ENVIRONMENT"


@dataclass(slots=True)
class LangfuseObserver:
    """Best-effort Langfuse bridge that degrades to no-op when unavailable."""

    enabled: bool = False
    capture_content: bool = False
    flush_on_finish: bool = True
    trace_name: str = "AIQuant GenericAgent"
    environment: str | None = None
    tags: list[str] | None = None
    client: Any = None
    propagate_attributes: Any = None
    reason: str = "disabled"

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> LangfuseObserver:
        payload = config or {}
        enabled = _env_bool(ENV_ENABLED, _as_bool(payload.get("enabled"), False))
        capture_content = _env_bool(ENV_CAPTURE_CONTENT, _as_bool(payload.get("capture_content"), False))
        flush_on_finish = _env_bool(ENV_FLUSH_ON_FINISH, _as_bool(payload.get("flush_on_finish"), True))
        environment = str(os.environ.get(ENV_ENVIRONMENT) or payload.get("environment") or "").strip() or None
        trace_name = str(payload.get("trace_name") or "AIQuant GenericAgent").strip() or "AIQuant GenericAgent"
        tags = [str(item) for item in payload.get("tags") or ["generic-agent", "ai-workbench"]]
        if not enabled:
            return cls(
                enabled=False,
                capture_content=capture_content,
                flush_on_finish=flush_on_finish,
                trace_name=trace_name,
                environment=environment,
                tags=tags,
                reason="disabled",
            )
        _sync_langfuse_env()
        if not os.environ.get("LANGFUSE_PUBLIC_KEY") or not os.environ.get("LANGFUSE_SECRET_KEY"):
            LOG.warning("langfuse disabled | reason=missing_credentials")
            return cls(
                enabled=False,
                capture_content=capture_content,
                flush_on_finish=flush_on_finish,
                trace_name=trace_name,
                environment=environment,
                tags=tags,
                reason="missing_credentials",
            )
        try:
            from langfuse import get_client, propagate_attributes
        except ImportError as exc:
            LOG.warning("langfuse disabled | reason=sdk_missing error={}", exc)
            return cls(
                enabled=False,
                capture_content=capture_content,
                flush_on_finish=flush_on_finish,
                trace_name=trace_name,
                environment=environment,
                tags=tags,
                reason="sdk_missing",
            )
        try:
            client = get_client()
        except Exception as exc:
            LOG.warning("langfuse disabled | reason=client_init_failed error={}", exc)
            return cls(
                enabled=False,
                capture_content=capture_content,
                flush_on_finish=flush_on_finish,
                trace_name=trace_name,
                environment=environment,
                tags=tags,
                reason="client_init_failed",
            )
        LOG.info(
            "langfuse enabled | trace_name={} capture_content={} environment={}",
            trace_name,
            capture_content,
            environment or "-",
        )
        return cls(
            enabled=True,
            capture_content=capture_content,
            flush_on_finish=flush_on_finish,
            trace_name=trace_name,
            environment=environment,
            tags=tags,
            client=client,
            propagate_attributes=propagate_attributes,
            reason="enabled",
        )

    @contextmanager
    def agent_run(
        self,
        *,
        message: str,
        session_id: int | str | None,
        project_root: Path,
        history_count: int,
    ) -> Iterator[ObservationHandle]:
        metadata = {
            "workspace": project_root.as_posix(),
            "history_messages": history_count,
            "message_chars": len(message or ""),
            "capture_content": self.capture_content,
        }
        input_payload = {"message": message} if self.capture_content else None
        with self._observation(
            name=self.trace_name,
            as_type="agent",
            input_payload=input_payload,
            metadata=metadata,
            session_id=session_id,
            propagate=True,
        ) as observation:
            yield observation

    @contextmanager
    def generation(self, *, turn: int, prompt: str, history_count: int) -> Iterator[ObservationHandle]:
        metadata = {
            "turn": turn,
            "history_messages": history_count,
            "prompt_chars": len(prompt or ""),
            "capture_content": self.capture_content,
        }
        input_payload = {"prompt": prompt} if self.capture_content else None
        with self._observation(
            name="generic_agent.llm",
            as_type="generation",
            input_payload=input_payload,
            metadata=metadata,
        ) as observation:
            yield observation

    @contextmanager
    def tool(self, *, tool_name: str, arguments: dict[str, Any]) -> Iterator[ObservationHandle]:
        metadata = {
            "tool": tool_name,
            "argument_keys": sorted(str(key) for key in arguments),
            "capture_content": self.capture_content,
        }
        input_payload = {"arguments": arguments} if self.capture_content else None
        with self._observation(
            name=f"generic_agent.tool.{tool_name or 'unknown'}",
            as_type="tool",
            input_payload=input_payload,
            metadata=metadata,
        ) as observation:
            yield observation

    def flush(self) -> None:
        if not self.enabled or not self.flush_on_finish:
            return
        try:
            self.client.flush()
        except Exception as exc:
            LOG.warning("langfuse flush failed | error={}", exc)

    @contextmanager
    def _observation(
        self,
        *,
        name: str,
        as_type: str,
        input_payload: Any,
        metadata: dict[str, Any],
        session_id: int | str | None = None,
        propagate: bool = False,
    ) -> Iterator[ObservationHandle]:
        if not self.enabled:
            yield ObservationHandle()
            return
        stack = ExitStack()
        try:
            if propagate:
                stack.enter_context(
                    self.propagate_attributes(
                        session_id=str(session_id) if session_id is not None else None,
                        metadata=metadata,
                        tags=self.tags or [],
                        trace_name=self.trace_name,
                        environment=self.environment,
                    )
                )
            observation = stack.enter_context(
                self.client.start_as_current_observation(
                    name=name,
                    as_type=as_type,
                    input=input_payload,
                    metadata=metadata,
                )
            )
        except Exception as exc:
            stack.close()
            LOG.warning("langfuse observation skipped | name={} type={} error={}", name, as_type, exc)
            yield ObservationHandle()
            return
        with stack:
            handle = ObservationHandle(observation=observation, capture_content=self.capture_content)
            try:
                yield handle
            except Exception as exc:
                handle.fail(exc)
                raise


@dataclass(slots=True)
class ObservationHandle:
    observation: Any = None
    capture_content: bool = False

    def finish(
        self,
        *,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
        model: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        if self.observation is None:
            return
        payload: dict[str, Any] = {
            "metadata": metadata or {},
            "level": "DEFAULT",
        }
        if self.capture_content:
            payload["output"] = output
        if model:
            payload["model"] = model
        usage_details = _usage_details(usage or {})
        if usage_details:
            payload["usage_details"] = usage_details
        try:
            self.observation.update(**payload)
        except Exception as exc:
            LOG.warning("langfuse observation update failed | error={}", exc)

    def fail(self, exc: Exception) -> None:
        if self.observation is None:
            return
        try:
            self.observation.update(level="ERROR", status_message=str(exc)[:500])
        except Exception as update_exc:
            LOG.warning("langfuse observation failure update failed | error={}", update_exc)


def _usage_details(usage: dict[str, Any]) -> dict[str, int]:
    details: dict[str, int] = {}
    mapping = {
        "prompt_tokens": "input",
        "completion_tokens": "output",
        "total_tokens": "total",
    }
    for source, target in mapping.items():
        value = usage.get(source)
        if value is None:
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number >= 0:
            details[target] = number
    return details


def _sync_langfuse_env() -> None:
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        if os.environ.get(name):
            continue
        value = resolve_env_value(name)
        if value:
            os.environ[name] = value


def _env_bool(name: str, fallback: bool) -> bool:
    if name not in os.environ:
        return fallback
    return _as_bool(os.environ.get(name), fallback)


def _as_bool(value: Any, fallback: bool) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return fallback
