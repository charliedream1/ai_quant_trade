"""Join shared observations when that optional platform component is present."""

from importlib import import_module


def traced(name, kind="span"):
    try:
        implementation = import_module("src.observability.instrumentation").traced
    except ModuleNotFoundError as exc:
        if exc.name not in {"src.observability", "src.observability.instrumentation"}:
            raise

        def decorate(function):
            return function

        return decorate
    return implementation(name, kind)
