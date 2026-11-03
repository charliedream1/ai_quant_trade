"""Cross-module callback error handling and duration records."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from inspect import isgeneratorfunction
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import gradio as gr
from src.core.exceptions import BusinessError
from src.core.logger import get_logger

from ..service_dispatch import lookup_method
from .errors import ui_error_message

CALLBACK_LOG = get_logger("frontend.callback")
SLOW_CALLBACK_MS = 1500
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def callback_location(fn: Callable[..., Any]) -> tuple[str, str]:
    """Resolve a Gradio callback to its service method and source position."""
    code = getattr(fn, "__code__", None)
    service_operation = (
        f"FrontendService.{getattr(fn, '__name__', '')}"
        if getattr(getattr(fn, "__self__", None), "frontend_callback_service", False)
        else ""
    )
    if code is not None and getattr(fn, "__name__", "") == "<lambda>":
        for name in reversed(code.co_names):
            method = lookup_method(name)
            if method is not None and hasattr(method, "__code__"):
                fn = method
                code = method.__code__
                service_operation = f"FrontendService.{name}"
                break
    name = service_operation or getattr(fn, "__qualname__", fn.__class__.__name__)
    if code is None:
        return name, "-"
    source = Path(code.co_filename)
    try:
        source = source.relative_to(PROJECT_ROOT)
    except ValueError:
        pass
    return name, f"{source}:{code.co_firstlineno}"


@contextmanager
def _callback_run(operation: str, source: str) -> Iterator[None]:
    operation_id = uuid4().hex
    started = perf_counter()
    CALLBACK_LOG.info(
        "frontend action backend method started | operation_id={} backend_method={} source={}",
        operation_id,
        operation,
        source,
    )
    try:
        yield
    except Exception as exc:
        message = ui_error_message(exc)
        failure_log = CALLBACK_LOG
        failure_log.log(
            "WARNING" if isinstance(exc, BusinessError) else "ERROR",
            "frontend action backend method failed | operation_id={} backend_method={} source={} duration_ms={:.0f} "
            "error_type={} message={}",
            operation_id,
            operation,
            source,
            (perf_counter() - started) * 1000,
            exc.__class__.__name__,
            message,
        )
        raise gr.Error(message, print_exception=False) from None
    else:
        duration_ms = (perf_counter() - started) * 1000
        finish_level = "WARNING" if duration_ms >= SLOW_CALLBACK_MS else "INFO"
        CALLBACK_LOG.log(
            finish_level,
            "frontend action backend method finished | operation_id={} backend_method={} source={} duration_ms={:.0f} "
            "slow_threshold_ms={}",
            operation_id,
            operation,
            source,
            duration_ms,
            SLOW_CALLBACK_MS,
        )


def safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Preserve streaming registration and handle errors throughout iteration."""
    operation, source = callback_location(fn)

    if isgeneratorfunction(fn):

        @wraps(fn)
        def streamed(*args: Any, **kwargs: Any) -> Iterator[Any]:
            with _callback_run(operation, source):
                yield from fn(*args, **kwargs)

        return streamed

    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with _callback_run(operation, source):
            return fn(*args, **kwargs)

    return wrapped
