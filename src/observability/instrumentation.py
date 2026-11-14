"""Small decorators keep tracing out of domain algorithms and preserve call context."""

from contextvars import copy_context
from functools import wraps
from inspect import signature
from time import perf_counter

from loguru import logger

from .config import observation_config
from .runtime import get_observer


def _inputs(function, args, kwargs):
    bound = signature(function).bind_partial(*args, **kwargs).arguments
    names = observation_config()["content_fields"]
    selected = {key: value for key, value in bound.items() if key in names}
    fields = {key: value for key, value in bound.items() if key in observation_config()["metadata_fields"]}
    for key, values in bound.items():
        if key in {"payload", "request", "selection", "config"} and isinstance(values, dict):
            fields.update(
                {key: value for key, value in values.items() if key in observation_config()["metadata_fields"]}
            )
    return selected, fields


def _finish(handle, result, started):
    fields = {"duration_ms": round((perf_counter() - started) * 1000)}
    if isinstance(result, dict):
        fields.update({key: result[key] for key in observation_config()["metadata_fields"] if key in result})
        handle.finish(
            output=result if handle.kind == "tool" else result.get("text"),
            model=result.get("model"),
            usage=result.get("usage"),
            metadata=fields,
        )
        if result.get("status") in {"failed", "cancelled"}:
            handle.fail(RuntimeError(result["status"]))
    else:
        handle.finish(metadata=fields)


def _safe_finish(handle, result, started):
    try:
        _finish(handle, result, started)
        return handle.identifiers()
    except Exception as exc:
        logger.warning("Observation result skipped | error_type={}", type(exc).__name__)
        return {}


def traced(name, kind="span"):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            observer = get_observer()
            if not observer.enabled:
                return function(*args, **kwargs)
            inputs, fields = _inputs(function, args, kwargs)
            started = perf_counter()
            with observer.observe(name, kind, input_payload=inputs, fields=fields) as handle:
                result = function(*args, **kwargs)
                identifiers = _safe_finish(handle, result, started)
                if kind == "generation" and isinstance(result, dict):
                    result = {**result, **identifiers}
                return result

        return wrapped

    return decorate


def traced_stream(name, kind="span"):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            observer = get_observer()
            if not observer.enabled:
                yield from function(*args, **kwargs)
                return

            def observed():
                inputs, fields = _inputs(function, args, kwargs)
                with observer.observe(name, kind, input_payload=inputs, fields=fields) as handle:
                    started, latest = perf_counter(), None
                    iterator = function(*args, **kwargs)
                    try:
                        for latest in iterator:
                            yield latest
                        _safe_finish(handle, latest, started)
                    finally:
                        iterator.close()

            context, iterator = copy_context(), observed()
            try:
                while True:
                    try:
                        item = context.run(next, iterator)
                    except StopIteration:
                        return
                    yield item
            finally:
                context.run(iterator.close)

        return wrapped

    return decorate


def submit_with_context(executor, function, *args, **kwargs):
    return executor.submit(copy_context().run, function, *args, **kwargs)
