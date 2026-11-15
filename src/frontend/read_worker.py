"""Trusted local IPC for interruptible page reads, without serializing UI closures."""

from __future__ import annotations

import os
import sys
from time import monotonic
from typing import Any

from src.core import config
from src.core.redaction import redact_text


def transferable(value: Any) -> Any:
    """Preserve Gradio's table display metadata without pickling Styler lambdas."""
    from pandas.io.formats.style import Styler

    if isinstance(value, Styler):
        from .table_wire import styled_table

        return styled_table(value)
    if isinstance(value, tuple):
        return tuple(transferable(item) for item in value)
    if isinstance(value, list):
        return [transferable(item) for item in value]
    if isinstance(value, dict):
        return {key: transferable(item) for key, item in value.items()}
    return value


def invoke(request, on_panel=None):
    """Resolve a named callback in the selected private runtime."""
    from src.core.exceptions import BusinessError
    from src.core.page_work import policy
    from src.core.panel_updates import PANEL_UPDATE
    from src.data.manager import REQUEST_MARKET
    from src.frontend.common.errors import ui_error_message
    from src.frontend.service_dispatch import CallbackServices

    name, args, kwargs, settings, market = request
    previous = config._SETTINGS
    if previous and previous.db_path != settings.db_path:
        from src.core.database import Database

        Database.reset_instance()
    config._SETTINGS = settings
    token = REQUEST_MARKET.set(market)
    panel_token = PANEL_UPDATE.set(on_panel)
    result: Any
    try:
        if name in policy()["source_methods"]:
            from src.engine.market.model_graph.evidence import EvidenceCorpus

            if name == "graph_resolve":
                from src.data import SecurityMasterService

                result = SecurityMasterService().resolve(*args)
            else:
                corpus = EvidenceCorpus(args[0])
                if name == "graph_local":
                    corpus.load_local()
                    result = corpus.sources
                elif name == "graph_read":
                    result = corpus.read(args[1])
                else:
                    result = corpus.search(args[1])
        elif name not in policy()["read_methods"]:
            raise ValueError("Callback is outside the transient-read policy")
        else:
            result = getattr(CallbackServices(), name)(*args, **kwargs)
        return True, transferable(result)
    except Exception as exc:
        return False, {
            "message": exc.message if isinstance(exc, BusinessError) else ui_error_message(exc),
            "code": exc.code if isinstance(exc, BusinessError) else None,
            "error_type": type(exc).__name__,
            "diagnostic": redact_text(str(exc))[: policy()["worker_error_chars"]],
        }
    finally:
        PANEL_UPDATE.reset(panel_token)
        REQUEST_MARKET.reset(token)


def serve(connection):
    """Accept only server-selected methods over a private parent-created pipe."""
    if sys.platform != "win32":
        os.setsid()
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    snapshots = []
    logger.add(
        lambda message: snapshots.append(message.record["message"]),
        level="DEBUG",
        filter=lambda record: record["message"].startswith("UI snapshot load |"),
    )
    from src.core.page_work import policy
    from src.core.work_progress import PROGRESS
    from src.core.workspace_config import workspace_config
    from src.observability.runtime import shutdown_observability

    connection.send(("ready", os.getpid()))
    while True:
        try:
            request = connection.recv()
        except EOFError:
            shutdown_observability()
            return
        if request is None:
            shutdown_observability()
            return
        snapshots.clear()
        last_stage, last_time = "", 0.0

        def emit(stage):
            nonlocal last_stage, last_time
            now = monotonic()
            if stage != last_stage or now - last_time >= workspace_config()["logging"]["progress_interval_seconds"]:
                connection.send(("progress", stage))
                last_stage, last_time = stage, now

        token = PROGRESS.set(emit)
        published = 0

        def publish(index, value, method=request[0]):
            nonlocal published
            count = policy()["progressive_methods"].get(method, 0)
            if not count:
                return
            if not 0 <= index < count or published >= policy()["max_panel_updates"]:
                raise ValueError("Invalid section publication")
            published += 1
            connection.send(("panel", index, transferable(value)))

        try:
            emit("Loading configured service")
            success, value = invoke(request, publish)
        finally:
            PROGRESS.reset(token)
        connection.send((success, value, snapshots))
