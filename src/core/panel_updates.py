"""Optional section publication leaves ordinary API/service return contracts unchanged."""

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

PANEL_UPDATE: ContextVar[Callable[[int, Any], None] | None] = ContextVar("panel_update", default=None)
PANEL_LOADING: ContextVar[Callable[[], None] | None] = ContextVar("panel_loading", default=None)
OBSERVATION_READY: ContextVar[Callable[[str, Any], None] | None] = ContextVar("observation_ready", default=None)


def panel_ready(index: int, value: Any) -> None:
    observer = PANEL_UPDATE.get()
    if observer is not None:
        observer(index, value)


def panel_values(builders):
    """Evaluate dependent presentation stages in order and publish each immediately."""
    values = []
    for index, build in enumerate(builders):
        value = build()
        values.append(value)
        panel_ready(index, value)
    return tuple(values)


def observation_ready(kind, value):
    observer = OBSERVATION_READY.get()
    if observer:
        observer(kind, value)


@contextmanager
def observe_references(index, convert):
    def publish(kind, references):
        if kind == "knowledge.references":
            panel_ready(index, convert(references))

    token = OBSERVATION_READY.set(publish)
    try:
        yield
    finally:
        OBSERVATION_READY.reset(token)
