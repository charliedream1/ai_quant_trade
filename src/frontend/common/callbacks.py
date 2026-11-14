"""Cross-module callback error handling and duration records."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from inspect import isgeneratorfunction, unwrap
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import gradio as gr
from gradio.context import LocalContext

from src.core.diagnostics_config import diagnostics_config
from src.core.exceptions import BusinessError
from src.core.logger import get_logger
from src.core.page_work import CURRENT_PAGE, PageCancelled, check
from src.core.stream_control import STREAM_STOP
from src.data.manager import REQUEST_MARKET

from ..service_dispatch import lookup_method
from .errors import ui_error_message

CALLBACK_LOG = get_logger("frontend.callback")
SLOW_CALLBACK_MS = diagnostics_config()["callbacks"]["slow_seconds"] * 1000
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def callback_location(fn: Callable[..., Any]) -> tuple[str, str]:
    """Resolve a Gradio callback to its service method and source position."""
    fn = unwrap(fn)
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
    request = LocalContext.request.get(None)
    from src.api.page_lifetime import request_page

    headers = getattr(request, "headers", None) or {}
    query = {key: [value] for key, value in (getattr(request, "query_params", None) or {}).items()}
    page = request_page(headers, query) or CURRENT_PAGE.get()
    page_token = CURRENT_PAGE.set(page)
    stop_token = STREAM_STOP.set(page.stopped) if page else None
    market = str((getattr(request, "headers", None) or {}).get("x-aiquant-market", "")).upper()
    token = REQUEST_MARKET.set(market) if market in {"CN", "HK", "US"} else None
    CALLBACK_LOG.debug(
        "frontend action backend method started | operation_id={} backend_method={} source={}",
        operation_id,
        operation,
        source,
    )
    try:
        check()
        yield
        check()
    except PageCancelled:
        CALLBACK_LOG.debug("Page callback cancelled | backend_method={}", operation)
        raise
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
        policy = diagnostics_config()["callbacks"]
        finish_level = policy["slow_success_level"] if duration_ms >= SLOW_CALLBACK_MS else policy["success_level"]
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
    finally:
        CURRENT_PAGE.reset(page_token)
        if stop_token is not None:
            STREAM_STOP.reset(stop_token)
        if token is not None:
            REQUEST_MARKET.reset(token)


def safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Preserve streaming registration and handle errors throughout iteration."""
    operation, source = callback_location(fn)

    if isgeneratorfunction(fn):

        @wraps(fn)
        def streamed(*args: Any, **kwargs: Any) -> Iterator[Any]:
            try:
                with _callback_run(operation, source):
                    for value in fn(*args, **kwargs):
                        check()
                        yield value
            except (PageCancelled, GeneratorExit):
                return

        return streamed

    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            with _callback_run(operation, source):
                result = fn(*args, **kwargs)
                check()
                return result
        except PageCancelled:
            return gr.skip()

    return wrapped
