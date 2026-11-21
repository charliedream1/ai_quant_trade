"""Cross-module callback error handling and duration records."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import copy_context
from functools import wraps
from inspect import isgeneratorfunction, unwrap
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from time import perf_counter
from typing import Any
from uuid import uuid4

import gradio as gr
from gradio.context import LocalContext

from src.core.diagnostics_config import diagnostics_config
from src.core.exceptions import BusinessError
from src.core.logger import get_logger
from src.core.page_work import CURRENT_PAGE, PageCancelled, check, policy
from src.core.panel_updates import PANEL_LOADING, PANEL_UPDATE
from src.core.paths import SOURCE_ROOT
from src.core.stream_control import STREAM_STOP
from src.core.workspace_config import workspace_config
from src.data.manager import REQUEST_MARKET

from ..service_dispatch import callback_registry, lookup_method
from .errors import ui_error_message

CALLBACK_LOG = get_logger("frontend.callback")
SLOW_CALLBACK_MS = diagnostics_config()["callbacks"]["slow_seconds"] * 1000


def callback_location(fn: Callable[..., Any]) -> tuple[str, str]:
    """Resolve a Gradio callback to its service method and source position."""
    fn = unwrap(fn)
    code = getattr(fn, "__code__", None)
    service_operation = (
        f"FrontendService.{getattr(fn, '__name__', '')}"
        if getattr(getattr(fn, "__self__", None), "frontend_callback_service", False)
        else ""
    )
    if code is not None and not service_operation:
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
        source = source.relative_to(SOURCE_ROOT)
    except ValueError:
        pass
    return name, f"{source}:{code.co_firstlineno}"


@contextmanager
def _callback_run(operation: str, source: str) -> Iterator[None]:
    operation_id = uuid4().hex
    method = operation.rsplit(".", 1)[-1]
    automatic = method in workspace_config()["logging"]["automatic_methods"]
    level = "DEBUG" if automatic else "INFO"
    action_log = get_logger("ui.action")
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
        action_log.log(level, "Action started | operation={} action={}", operation_id[:12], operation)
        yield
        check()
    except PageCancelled:
        action_log.log(level, "Action cancelled | operation={} action={}", operation_id[:12], operation)
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
        action_log.log(
            level,
            "Action completed | operation={} action={} duration_ms={:.0f}",
            operation_id[:12],
            operation,
            duration_ms,
        )
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


def safe(fn: Callable[..., Any], *, cancel_outputs: int = 1) -> Callable[..., Any]:
    """Preserve streaming registration and handle errors throughout iteration."""
    operation, source = callback_location(fn)
    output_count = policy()["progressive_methods"].get(operation.removeprefix("FrontendService."))
    original = unwrap(fn)
    if getattr(original, "__self__", None) is None:
        code = getattr(original, "__code__", None)
        referenced = set(code.co_names).intersection(callback_registry()) if code else set()
        if len(referenced) > 1:
            output_count = None

    if output_count and not isgeneratorfunction(fn):

        @wraps(fn)
        def sections(*args: Any, **kwargs: Any) -> Iterator[Any]:
            def execute():
                page_owned = False
                try:
                    with _callback_run(operation, source):
                        page_owned = CURRENT_PAGE.get() is not None
                        if CURRENT_PAGE.get() is None:
                            yield fn(*args, **kwargs)
                        else:
                            yield from _section_call(
                                fn, args, kwargs, output_count, sections.__dict__.get("aiquant_output_classes")
                            )
                except (PageCancelled, GeneratorExit):
                    return
                except gr.Error as exc:
                    if not page_owned:
                        raise
                    gr.Warning(str(exc))

            yield from _context_iterator(execute())

        sections.__dict__["aiquant_progressive"] = True
        return sections

    if isgeneratorfunction(fn):

        @wraps(fn)
        def streamed(*args: Any, **kwargs: Any) -> Iterator[Any]:
            def execute():
                try:
                    with _callback_run(operation, source):
                        for value in fn(*args, **kwargs):
                            check()
                            yield value
                except (PageCancelled, GeneratorExit):
                    return

            yield from _context_iterator(execute())

        return streamed

    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            with _callback_run(operation, source):
                result = fn(*args, **kwargs)
                check()
                return result
        except PageCancelled:
            return gr.skip() if cancel_outputs == 1 else tuple(gr.skip() for _ in range(cancel_outputs))

    return wrapped


def _context_iterator(iterator):
    """Gradio may advance a synchronous generator on different executor threads."""
    context = copy_context()
    try:
        while True:
            try:
                value = context.run(next, iterator)
            except StopIteration:
                return
            yield value
    finally:
        context.run(iterator.close)


def enable_progressive_queue(blocks):
    """Both installed Gradio versions stream generator events through their queue protocol."""
    for function in blocks.fns.values():
        if getattr(function.fn, "aiquant_progressive", False):
            function.queue = True
            function.show_progress = "hidden"
            function.fn.__dict__["aiquant_output_classes"] = [
                list(component.elem_classes or []) if hasattr(component, "elem_classes") else None
                for component in function.outputs
            ]
    return blocks


def _section_value(value, classes):
    """SDK updates are control envelopes, including no-ops, rather than component values."""
    if isinstance(value, dict) and value.get("__type__") == "update":
        return value
    return gr.update(value=value, elem_classes=[*classes, "section-ready"]) if classes is not None else value


def _section_snapshot(values):
    """Gradio removes value from update envelopes during postprocessing."""
    copied = tuple(
        dict(value) if isinstance(value, dict) and value.get("__type__") == "update" else value for value in values
    )
    return copied if len(copied) > 1 else copied[0]


def _section_call(fn, args, kwargs, output_count, classes=None):
    """The parent adapter only waits for cancellable owned reads; business work stays in workers."""
    from src.frontend.page_reads import READ_STOP

    events: Queue = Queue()
    stop = Event()
    classes = classes or [None] * output_count
    visible = [
        gr.update(elem_classes=[*style, "section-loading"]) if style is not None else gr.skip() for style in classes
    ]
    completed = set()

    def publish(index, value):
        if not stop.is_set():
            events.put(("panel", (index, value)))

    def run():
        token = PANEL_UPDATE.set(publish)
        loading_token = PANEL_LOADING.set(lambda: events.put(("loading", None)))
        cancel_token = READ_STOP.set(stop)
        try:
            result = fn(*args, **kwargs)
            events.put(("result", result))
        except BaseException as exc:
            events.put(("error", exc))
        finally:
            PANEL_UPDATE.reset(token)
            PANEL_LOADING.reset(loading_token)
            READ_STOP.reset(cancel_token)

    context = copy_context()
    thread = Thread(target=context.run, args=(run,), daemon=True, name="page-section-adapter")
    thread.start()
    try:
        announced = False
        while True:
            check()
            try:
                kind, value = events.get(timeout=policy()["poll_seconds"])
            except Empty:
                continue
            if kind == "loading":
                if not announced:
                    announced = True
                    yield _section_snapshot(visible)
            elif kind == "panel":
                index, data = value
                completed.add(index)
                visible[index] = _section_value(data, classes[index])
                announced = True
                yield _section_snapshot(visible)
            elif kind == "error":
                for index, style in enumerate(classes):
                    if index not in completed and style is not None:
                        visible[index] = gr.update(elem_classes=[*style, "section-failed"])
                yield _section_snapshot(visible)
                raise value
            else:
                if isinstance(value, tuple) and len(value) == output_count:
                    yield _section_snapshot([_section_value(item, classes[index]) for index, item in enumerate(value)])
                else:
                    yield value
                return
    finally:
        stop.set()
        thread.join(timeout=policy()["shutdown_seconds"])
