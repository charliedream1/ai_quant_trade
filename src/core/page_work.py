"""Capability-scoped lifetimes for transient browser work, independent of durable jobs."""

from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from threading import Event, RLock, Thread, current_thread
from time import monotonic

import yaml

from src.core.config import PROJECT_ROOT
from src.core.logger import get_logger


@lru_cache(maxsize=1)
def policy() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/ui/page_work.yaml").read_text(encoding="utf-8"))


class PageCancelled(BaseException):
    """Expected abandonment; source fallback handlers must not turn it into another request."""


@dataclass(eq=False)
class PageWork:
    owner: str
    revision: int
    stopped: Event = field(default_factory=Event)
    touched: float = field(default_factory=monotonic)
    callbacks: list[Callable[[], None]] = field(default_factory=list)
    cancelled: Callable[[], bool] | None = None

    def is_set(self) -> bool:
        return self.stopped.is_set() or bool(self.cancelled and self.cancelled())

    def wait(self, seconds: float) -> bool:
        return self.stopped.wait(seconds)


CURRENT_PAGE: ContextVar[PageWork | None] = ContextVar("current_page_work", default=None)
LOCK = RLock()
PAGES: dict[str, PageWork] = {}
WATCHER_STOP = Event()
WATCHER: Thread | None = None


def identity(owner: str, revision: str | int) -> tuple[str, int]:
    if not re.fullmatch(r"[a-f0-9]{32}", str(owner)):
        raise ValueError("Invalid page capability")
    number = int(revision)
    if not 1 <= number <= policy()["max_revision"]:
        raise ValueError("Invalid navigation revision")
    return owner, number


def _stop(page: PageWork) -> None:
    page.stopped.set()
    callbacks, page.callbacks = page.callbacks, []
    for callback in callbacks:
        try:
            callback()
        except Exception as exc:
            get_logger("page.lifecycle").debug("Cancellation hook finished with {}", type(exc).__name__)


def activate(owner: str, revision: str | int) -> PageWork:
    owner, number = identity(owner, revision)
    with LOCK:
        old = PAGES.get(owner)
        if old and number <= old.revision:
            if number == old.revision:
                old.touched = monotonic()
                return old
            cancelled = PageWork(owner, number)
            cancelled.stopped.set()
            return cancelled
        if not old and len(PAGES) >= policy()["max_documents"]:
            raise ValueError("Page lifetime capacity reached; retry after inactive documents expire")
        if old:
            _stop(old)
        page = PageWork(owner, number)
        PAGES[owner] = page
        return page


def resolve(owner: str, revision: str | int) -> PageWork:
    owner, number = identity(owner, revision)
    with LOCK:
        page = PAGES.get(owner)
        if page is None or number > page.revision:
            return activate(owner, number)
        if page.revision == number:
            page.touched = monotonic()
            return page
        cancelled = PageWork(owner, number)
        cancelled.stopped.set()
        return cancelled


def deactivate(owner: str, revision: str | int) -> None:
    owner, number = identity(owner, revision)
    with LOCK:
        page = PAGES.get(owner)
        if page and page.revision == number:
            _stop(page)


def check() -> None:
    page = CURRENT_PAGE.get()
    if page and page.is_set():
        raise PageCancelled()


@contextmanager
def context(page: PageWork | None):
    token = CURRENT_PAGE.set(page)
    try:
        check()
        yield
        check()
    finally:
        CURRENT_PAGE.reset(token)


def on_cancel(page: PageWork, callback: Callable[[], None]) -> Callable[[], None]:
    with LOCK:
        if page.is_set():
            callback()
        else:
            page.callbacks.append(callback)

    def detach():
        with LOCK:
            if callback in page.callbacks:
                page.callbacks.remove(callback)

    return detach


RUN_CONSUMERS: dict[tuple[str, str], set[PageWork | None]] = {}


def own_run(kind: str, identifier: str, cancel: Callable[[], None]) -> None:
    """Only creators acquire cancellation rights; a viewer never calls this function."""
    page = CURRENT_PAGE.get()
    key = kind, identifier
    with LOCK:
        consumers = RUN_CONSUMERS.setdefault(key, set())
        if page in consumers:
            return
        consumers.add(page)
    if page is None:
        return

    def leave():
        with LOCK:
            current = RUN_CONSUMERS.get(key, set())
            current.discard(page)
            if current:
                return
            RUN_CONSUMERS.pop(key, None)
        cancel()

    on_cancel(page, leave)


def finish_run(kind: str, identifier: str) -> None:
    with LOCK:
        RUN_CONSUMERS.pop((kind, identifier), None)


def start() -> None:
    global WATCHER
    if WATCHER and WATCHER.is_alive():
        return
    WATCHER_STOP.clear()

    def expire():
        while not WATCHER_STOP.wait(policy()["sweep_seconds"]):
            with LOCK:
                for owner, page in list(PAGES.items()):
                    age = monotonic() - page.touched
                    if age > policy()["idle_seconds"]:
                        _stop(page)
                    if age > policy()["retention_seconds"]:
                        PAGES.pop(owner, None)

    WATCHER = Thread(target=expire, daemon=True, name="page-lifetimes")
    WATCHER.start()


def shutdown() -> None:
    global WATCHER
    WATCHER_STOP.set()
    with LOCK:
        for page in PAGES.values():
            _stop(page)
        PAGES.clear()
        RUN_CONSUMERS.clear()
    if WATCHER is not None and WATCHER is not current_thread():
        WATCHER.join(timeout=policy()["shutdown_seconds"])
    WATCHER = None
