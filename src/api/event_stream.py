"""SSE representation of actual domain generator events."""

import asyncio
import json
from collections.abc import Iterable
from contextvars import copy_context
from queue import Empty, Full, Queue
from threading import BoundedSemaphore, Event, Thread
from typing import Any

from src.core.exceptions import BusinessError
from src.core.redaction import redact_text
from src.core.security_config import security_config
from src.core.stream_control import STREAM_STOP
from src.core.timeutil import utc_now_iso

SLOTS = BoundedSemaphore(security_config()["limits"]["sse_clients"])


def _encode_events(events: Iterable[dict[str, Any]]):
    sequence = 0
    try:
        for event in events:
            sequence += 1
            payload = {"event_id": sequence, "time": utc_now_iso(), **event}
            yield "data: " + json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n\n"
    except Exception as exc:
        code = exc.code if isinstance(exc, BusinessError) else 5999
        payload = {
            "event_id": sequence + 1,
            "type": "result",
            "data": {
                "code": code,
                "message": redact_text(str(exc))
                if isinstance(exc, BusinessError)
                else "执行未完成，请查看该运行的错误记录",
                "data": None,
            },
        }
        yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


async def sse_events(events: Iterable[dict[str, Any]]):
    if not SLOTS.acquire(blocking=False):
        yield (
            "data: "
            + json.dumps(
                {"type": "result", "data": {"code": 429, "message": "事件连接数已达上限", "data": None}},
                ensure_ascii=False,
            )
            + "\n\n"
        )
        return
    channel: Queue = Queue(maxsize=security_config()["limits"]["sse_chunks"])
    stopped = Event()
    token = STREAM_STOP.set(stopped)

    def offer(value):
        while not stopped.is_set():
            try:
                channel.put(value, timeout=0.1)
                return
            except Full:
                continue

    def produce():
        iterator = _encode_events(events)
        try:
            for chunk in iterator:
                if stopped.is_set():
                    break
                offer(chunk)
        except GeneratorExit:
            pass
        finally:
            try:
                iterator.close()
                close = getattr(events, "close", None)
                if close:
                    close()
            finally:
                offer(None)
                SLOTS.release()

    context = copy_context()
    try:
        Thread(target=context.run, args=(produce,), daemon=True, name="sse-events").start()
    except Exception:
        SLOTS.release()
        STREAM_STOP.reset(token)
        raise
    try:
        while True:
            try:
                chunk = channel.get_nowait()
            except Empty:
                await asyncio.sleep(security_config()["limits"]["sse_poll_seconds"])
                continue
            if chunk is None:
                return
            yield chunk
    finally:
        stopped.set()
        STREAM_STOP.reset(token)
