"""Bounded reusable workers and consumer-aware cancellation for page callbacks."""

from __future__ import annotations

import hashlib
import multiprocessing

# Only hashes server-owned arguments; no client pickle is accepted.
import pickle  # nosec B403
from concurrent.futures import Future
from dataclasses import dataclass, field
from threading import Condition, Event, RLock, Thread
from time import monotonic
from typing import Any
from uuid import uuid4

from src.agent.model_rate_limit import release_worker_slots
from src.core.config import get_settings
from src.core.exceptions import BusinessError
from src.core.logger import get_logger
from src.core.page_work import CURRENT_PAGE, PageCancelled, PageWork, check, on_cancel, policy
from src.core.process_control import stop_process_tree
from src.data import current_market

from .read_worker import serve

LOCK = RLock()
CAPACITY = Condition()
SLOTS: list[Any] = []
BUSY: set[int] = set()
STOP = Event()
WARMING = False


@dataclass
class ReadJob:
    request: tuple
    future: Future = field(default_factory=Future)
    stop: Event = field(default_factory=Event)
    consumers: dict[PageWork, int] = field(default_factory=dict)


JOBS: dict[str, ReadJob] = {}


def _new_slot():
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=serve, args=(child,), daemon=True, name="page-read-worker")
    process.start()
    child.close()
    return process, parent


def start(*, warm: bool = False) -> None:
    """Warm the pool off the event loop; no source calls occur during warmup."""
    global WARMING
    STOP.clear()
    if not warm:
        return
    with CAPACITY:
        if WARMING:
            return
        WARMING = True

    def warm_pool():
        with CAPACITY:
            while not STOP.is_set() and len(SLOTS) < policy()["workers"]:
                SLOTS.append(_new_slot())
            CAPACITY.notify_all()

    Thread(target=warm_pool, daemon=True, name="page-read-warmup").start()


def _slot(job: ReadJob, deadline: float):
    groups = policy()["affinity_groups"]
    group = next((index for index, names in enumerate(groups) if job.request[0] in names), None)
    eligible = (
        {min(group, policy()["workers"] - 1)}
        if group is not None
        else set(range(min(len(groups), policy()["workers"] - 1), policy()["workers"]))
    )
    with CAPACITY:
        while not STOP.is_set() and not job.stop.is_set() and monotonic() < deadline:
            for index, item in enumerate(SLOTS):
                if index in eligible and index not in BUSY:
                    BUSY.add(index)
                    if item is None:
                        item = SLOTS[index] = _new_slot()
                    return index, item
            if len(SLOTS) < policy()["workers"]:
                index = len(SLOTS)
                SLOTS.append(_new_slot())
                if index in eligible:
                    BUSY.add(index)
                    return index, SLOTS[index]
                continue
            CAPACITY.wait(policy()["poll_seconds"])
    if not STOP.is_set() and not job.stop.is_set():
        raise TimeoutError("Page read exceeded its capacity-wait deadline")
    raise PageCancelled()


def _terminate(slot) -> None:
    process, connection = slot
    if process.is_alive():
        stop_process_tree(process)
    process.join(timeout=policy()["shutdown_seconds"])
    connection.close()
    process.close()


def _execute(key: str, job: ReadJob) -> None:
    slot = None
    index = None
    reusable = False
    try:
        deadline = monotonic() + policy()["read_deadline_seconds"]
        index, slot = _slot(job, deadline)
        process, connection = slot
        connection.send(job.request)
        while not STOP.is_set() and not job.stop.is_set():
            if connection.poll(policy()["poll_seconds"]):
                message = connection.recv()
                success, value = message[:2]
                for snapshot in message[2] if len(message) > 2 else []:
                    get_logger("page.worker").debug("{}", snapshot)
                reusable = True
                if not success:
                    if isinstance(value, dict):
                        if value.get("code") is not None:
                            raise BusinessError(value["code"], value["message"])
                        if value.get("error_type") not in {None, "ValueError"}:
                            get_logger("page.worker").error(
                                "Page read failed | method={} error_type={} detail={}",
                                job.request[0],
                                value["error_type"],
                                value.get("diagnostic", ""),
                            )
                        raise ValueError(value["message"])
                    raise ValueError(value)
                job.future.set_result(value)
                return
            if not process.is_alive():
                raise RuntimeError("Page read worker stopped before producing a result")
            if monotonic() >= deadline:
                raise TimeoutError("Page read exceeded its configured deadline")
        raise PageCancelled()
    except BaseException as exc:
        job.future.set_exception(exc)
    finally:
        if slot is not None and not reusable:
            pid = slot[0].pid
            _terminate(slot)
            release_worker_slots(job.request[3].db_path, pid)
        if index is not None:
            with CAPACITY:
                if not reusable:
                    SLOTS[index] = None
                BUSY.discard(index)
                CAPACITY.notify_all()
        with LOCK:
            if JOBS.get(key) is job:
                JOBS.pop(key, None)


def read(name: str, args: tuple, kwargs: dict) -> Any:
    page = CURRENT_PAGE.get()
    if page is None:
        raise RuntimeError("Page worker requires a browser lifetime")
    check()
    request = name, args, kwargs, get_settings(), current_market()
    key = hashlib.sha256(pickle.dumps(request)).hexdigest() if name in policy()["share_methods"] else uuid4().hex
    with LOCK:
        job = JOBS.get(key)
        if job is None or job.stop.is_set():
            if len(JOBS) >= policy()["max_pending_reads"]:
                raise ValueError("Too many page reads are waiting; please retry")
            job = ReadJob(request)
            JOBS[key] = job
            Thread(target=_execute, args=(key, job), daemon=True, name="page-read").start()
        job.consumers[page] = job.consumers.get(page, 0) + 1

    left = False

    def leave():
        nonlocal left
        with LOCK:
            if left:
                return
            left = True
            count = job.consumers.get(page, 0)
            if count > 1:
                job.consumers[page] = count - 1
            else:
                job.consumers.pop(page, None)
            if not job.consumers:
                job.stop.set()

    detach = on_cancel(page, leave)
    try:
        while not job.future.done():
            check()
            page.wait(policy()["poll_seconds"])
        check()
        return job.future.result()
    finally:
        detach()
        leave()


def shutdown() -> None:
    global WARMING
    STOP.set()
    with LOCK:
        for job in JOBS.values():
            job.stop.set()
    deadline = monotonic() + policy()["shutdown_seconds"] * 2
    with CAPACITY:
        while BUSY and monotonic() < deadline:
            CAPACITY.wait(policy()["poll_seconds"])
        for index, slot in enumerate(SLOTS):
            if slot is not None and index not in BUSY:
                if slot[0].is_alive():
                    slot[1].send(None)
                    slot[0].join(timeout=policy()["shutdown_seconds"])
                _terminate(slot)
        if not BUSY:
            SLOTS.clear()
            WARMING = False
