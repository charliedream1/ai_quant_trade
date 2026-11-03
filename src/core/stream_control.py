"""Disconnect-aware waits shared by synchronous UI/CLI and asynchronous SSE bridges."""

from contextvars import ContextVar
from threading import Event

STREAM_STOP: ContextVar[Event | None] = ContextVar("stream_stop", default=None)


def stream_cancelled() -> bool:
    event = STREAM_STOP.get()
    return bool(event and event.is_set())


def stream_pause(seconds: float):
    event = STREAM_STOP.get()
    if event is None:
        Event().wait(seconds)
    elif event.wait(seconds):
        raise GeneratorExit
