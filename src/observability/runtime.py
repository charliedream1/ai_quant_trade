"""Best-effort observation lifetimes isolated from business results and exceptions."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from importlib.util import find_spec
from threading import Lock, Thread
from typing import Any
from urllib.parse import urlsplit

from loguru import logger

from .config import enabled, observation_config, settings
from .privacy import clean_text, content, privacy_scope, sdk_mask
from .privacy import metadata as safe_metadata

ACTIVE: ContextVar[Any] = ContextVar("aiquant_observation", default=None)
LOCK = Lock()
INSTANCE: Any = None


@dataclass
class Observation:
    observation: Any = None
    capture_content: bool = False
    kind: str = "span"

    def finish(self, *, output=None, metadata=None, model=None, usage=None) -> None:
        if self.observation is None:
            return
        payload: dict[str, Any] = {"metadata": safe_metadata(metadata), "level": "DEFAULT"}
        if self.capture_content:
            payload["output"] = content(output)
        if self.kind == "generation":
            if model:
                payload["model"] = clean_text(str(model), observation_config()["max_metadata_chars"])
            details = {}
            for key, target in observation_config()["usage_fields"].items():
                value = (usage or {}).get(key)
                if type(value) is int and value >= 0:
                    details[target] = value
            if details:
                payload["usage_details"] = details
        self._update(payload)

    def fail(self, exc: BaseException) -> None:
        self._update(
            {
                "level": "ERROR",
                "status_message": type(exc).__name__,
                "metadata": {
                    "error_type": type(exc).__name__,
                    "status": "cancelled"
                    if isinstance(exc, GeneratorExit) or type(exc).__name__ == "CancelledError"
                    else "failed",
                },
            }
        )

    def _update(self, payload) -> None:
        if self.observation is None:
            return
        try:
            self.observation.update(**payload)
        except Exception as exc:
            logger.warning("Observation update skipped | error_type={}", type(exc).__name__)

    def identifiers(self) -> dict:
        if self.observation is None:
            return {}
        return {
            key: getattr(self.observation, attr)
            for key, attr in [("trace_id", "trace_id"), ("observation_id", "id")]
            if getattr(self.observation, attr, None)
        }


class Observer:
    def __init__(self, cfg=None, client=None, reason="disabled", provider=None):
        self.cfg = cfg if cfg is not None else observation_config() if client is not None else {}
        self.client, self.reason = client, reason
        self.enabled = client is not None
        self.capture_content = bool(self.cfg.get("capture_content", False))
        self.provider = provider

    @contextmanager
    def observe(self, name: str, kind="span", *, input_payload=None, fields=None):
        if not self.enabled:
            yield Observation()
            return
        current = ACTIVE.get()
        if kind == "generation" and current and current.kind == "generation":
            yield current
            return
        scope = privacy_scope(refresh=kind == "generation")
        try:
            scope.__enter__()
        except Exception as exc:
            logger.warning("Observation privacy initialization skipped | error_type={}", type(exc).__name__)
            yield Observation()
            return
        try:
            with self._observe(name, kind, input_payload=input_payload, fields=fields) as handle:
                yield handle
        finally:
            scope.__exit__(None, None, None)

    @contextmanager
    def _observe(self, name: str, kind="span", *, input_payload=None, fields=None):
        prior = ACTIVE.get()
        if kind == "generation" and prior and prior.kind == "generation":
            yield prior
            return
        if not self.enabled:
            yield Observation()
            return
        manager = propagation = None
        try:
            from langfuse import propagate_attributes

            safe = safe_metadata(fields)
            name = clean_text(str(name), self.cfg["max_metadata_chars"])
            propagation = propagate_attributes(
                session_id=str(safe["session_id"]) if safe.get("session_id") is not None else None,
                trace_name=name if prior is None else None,
                tags=[clean_text(str(tag), self.cfg["max_metadata_chars"]) for tag in self.cfg["tags"]],
            )
            propagation.__enter__()
            manager = self.client.start_as_current_observation(
                name=name,
                as_type=kind,
                input=content(input_payload) if self.capture_content else None,
                metadata=safe_metadata(fields),
            )
            handle = Observation(manager.__enter__(), self.capture_content, kind)
        except Exception as exc:
            if propagation is not None:
                try:
                    propagation.__exit__(None, None, None)
                except Exception as cleanup_exc:
                    logger.warning("Observation setup cleanup skipped | error_type={}", type(cleanup_exc).__name__)
            logger.warning("Observation start skipped | error_type={}", type(exc).__name__)
            yield Observation()
            return
        token = ACTIVE.set(handle)
        try:
            yield handle
        except BaseException as exc:
            handle.fail(exc)
            raise
        finally:
            ACTIVE.reset(token)
            try:
                # Exception details are handled above; SDK traceback recording can expose local paths.
                manager.__exit__(None, None, None)
            except Exception as exc:
                logger.warning("Observation close skipped | error_type={}", type(exc).__name__)
            finally:
                try:
                    propagation.__exit__(None, None, None)
                except Exception as exc:
                    logger.warning("Observation propagation close skipped | error_type={}", type(exc).__name__)

    def shutdown(self):
        if not self.enabled:
            return

        def finish():
            try:
                self.client.shutdown()
            except Exception as exc:
                logger.warning("Observation shutdown skipped | error_type={}", type(exc).__name__)
            finally:
                if self.provider is not None:
                    try:
                        self.provider.shutdown()
                    except Exception as exc:
                        logger.warning("Observation provider shutdown skipped | error_type={}", type(exc).__name__)

        worker = Thread(target=finish, name="observation-shutdown", daemon=True)
        worker.start()
        worker.join(self.cfg["shutdown_timeout_seconds"])


def _initialize() -> Observer:
    cfg = settings()
    if not all(cfg.get(key) for key in ("public_key", "secret_key", "base_url")):
        return Observer(cfg, reason="missing_configuration")
    try:
        parsed = urlsplit(cfg["base_url"])
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            return Observer(cfg, reason="invalid_endpoint")
        from langfuse import Langfuse
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

        provider = TracerProvider(sampler=TraceIdRatioBased(cfg["sample_rate"]))
        client = Langfuse(
            public_key=cfg["public_key"],
            secret_key=cfg["secret_key"],
            base_url=cfg["base_url"],
            environment=clean_text(cfg["environment"], cfg["max_metadata_chars"]),
            sample_rate=cfg["sample_rate"],
            timeout=cfg["export_timeout_seconds"],
            flush_at=cfg["flush_at"],
            flush_interval=cfg["flush_interval_seconds"],
            mask=sdk_mask,
            should_export_span=lambda span: (
                span.instrumentation_scope is not None and span.instrumentation_scope.name == "langfuse-sdk"
            ),
            tracer_provider=provider,
        )
        return Observer(cfg, client, "enabled", provider)
    except ImportError:
        return Observer(cfg, reason="sdk_missing")
    except Exception as exc:
        logger.warning("Observation initialization skipped | error_type={}", type(exc).__name__)
        return Observer(cfg, reason="initialization_failed")


DISABLED = Observer()


def get_observer() -> Observer:
    global INSTANCE
    try:
        requested = enabled()
    except Exception as exc:
        logger.warning("Observation configuration skipped | error_type={}", type(exc).__name__)
        return DISABLED
    if not requested:
        return DISABLED
    with LOCK:
        if INSTANCE is None:
            try:
                INSTANCE = _initialize()
            except Exception as exc:
                logger.warning("Observation initialization skipped | error_type={}", type(exc).__name__)
                return DISABLED
    return INSTANCE


def current_observation() -> Observation:
    return ACTIVE.get() or Observation()


def observation_status() -> dict:
    observer = INSTANCE
    requested = enabled()
    return {
        "enabled": requested,
        "initialized": observer is not None,
        "active": bool(requested and observer and observer.enabled),
        "reason": observer.reason if observer else "not_initialized",
        "sdk_installed": find_spec("langfuse") is not None,
        "capture_content": settings()["capture_content"],
    }


def shutdown_observability() -> None:
    global INSTANCE
    with LOCK:
        observer, INSTANCE = INSTANCE, None
    if observer:
        observer.shutdown()
