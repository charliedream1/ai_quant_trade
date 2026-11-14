"""Keep Windows client-close transport noise separate from application failures."""

import asyncio
import sys
from collections.abc import Callable

from src.core.logger import get_logger


def expected_client_reset(context: dict) -> bool:
    exception = context.get("exception")
    callback = getattr(context.get("handle"), "_callback", None)
    return (
        isinstance(exception, ConnectionResetError)
        and getattr(exception, "winerror", None) == 10054
        and getattr(callback, "__module__", "") == "asyncio.proactor_events"
        and getattr(callback, "__name__", "") == "_call_connection_lost"
    )


def install_client_close_diagnostics() -> Callable[[], None]:
    if sys.platform != "win32":
        return lambda: None
    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()

    def handle(target_loop, context):
        if expected_client_reset(context):
            get_logger("backend.connection").debug("Client closed a Windows transport connection")
        elif previous:
            previous(target_loop, context)
        else:
            target_loop.default_exception_handler(context)

    loop.set_exception_handler(handle)

    def restore():
        if loop.get_exception_handler() is handle:
            loop.set_exception_handler(previous)

    return restore
