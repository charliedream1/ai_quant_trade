"""Trusted local IPC for interruptible page reads, without serializing UI closures."""

from __future__ import annotations

import os
import sys
from typing import Any

from src.core.redaction import redact_text


def transferable(value: Any) -> Any:
    """Preserve Gradio's table display metadata without pickling Styler lambdas."""
    from pandas.io.formats.style import Styler

    if isinstance(value, Styler):
        import gradio as gr

        return {
            "headers": list(value.data.columns),
            "data": gr.Dataframe.get_cell_data(value),
            "metadata": gr.Dataframe.get_metadata(value),
        }
    if isinstance(value, tuple):
        return tuple(transferable(item) for item in value)
    if isinstance(value, list):
        return [transferable(item) for item in value]
    if isinstance(value, dict):
        return {key: transferable(item) for key, item in value.items()}
    return value


def invoke(request):
    """Resolve a named callback in the selected private runtime."""
    from src.core import config
    from src.core.exceptions import BusinessError
    from src.core.page_work import policy
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
    # Load the domain facade once during warmup, before the first interactive read.
    from src.frontend.service import foundation  # noqa: F401
    from src.observability.runtime import shutdown_observability

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
        success, value = invoke(request)
        connection.send((success, value, snapshots))
