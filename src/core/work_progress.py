"""Bounded stage events cross worker boundaries without carrying source content."""

from collections.abc import Callable
from contextvars import ContextVar

PROGRESS: ContextVar[Callable[[str], None] | None] = ContextVar("work_progress", default=None)


def progress(stage: str) -> None:
    observer = PROGRESS.get()
    if observer is not None:
        observer(stage)
