"""Bound synchronous work off the event loop, with independent capacity per class."""

import asyncio
from functools import partial
from weakref import WeakKeyDictionary

import anyio

from src.core.exceptions import BusinessError, ErrorCode
from src.core.security_config import security_config

LIMITERS: WeakKeyDictionary = WeakKeyDictionary()


async def blocking_call(function, *args, group="upload", **kwargs):
    loop = asyncio.get_running_loop()
    limits = LIMITERS.setdefault(loop, {})
    if group not in limits:
        limits[group] = anyio.CapacityLimiter(1 if group == "ui_build" else security_config()["limits"]["io_workers"])
    return await anyio.to_thread.run_sync(partial(function, *args, **kwargs), limiter=limits[group])


async def read_upload(file, maximum: int) -> bytes:
    value = await file.read(maximum + 1)
    if len(value) > maximum:
        raise BusinessError(ErrorCode.INVALID_PARAM, security_config()["messages"]["too_large"])
    return value
