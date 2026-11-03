"""Exercise the Gradio generator contract at the registered callback boundary."""

from inspect import isgeneratorfunction

import pytest
from loguru import logger

import gradio as gr
from src.frontend.common.callbacks import safe
from src.frontend.services import FrontendService


def test_safe_preserves_stream_outputs_and_logs_completion_after_iteration():
    logs = []
    sink = logger.add(lambda message: logs.append(str(message)))

    def stream():
        yield (1, [], "", [], "received", [])
        yield (1, [], "", [], "completed", [])

    try:
        wrapped = safe(stream)
        assert isgeneratorfunction(wrapped)
        result = wrapped()
        assert len(next(result)) == 6
        assert not any("method finished" in message for message in logs)
        assert len(list(result)) == 1
        assert sum("method finished" in message for message in logs) == 1
    finally:
        logger.remove(sink)


def test_safe_handles_failure_after_first_stream_event():
    def stream():
        yield "received"
        raise ValueError("stream failed")

    result = safe(stream)()
    assert next(result) == "received"
    with pytest.raises(gr.Error, match="stream failed"):
        next(result)
    assert safe(lambda: "sync")() == "sync"


def test_workbench_callback_has_six_stream_outputs_and_persistent_history(client):
    service = FrontendService()
    session = service.ai_console_new_session("stream-contract", "test")[1]
    callback = safe(service.ai_console_send_stream)
    assert isgeneratorfunction(callback)
    events = list(callback(session, "你好", [], "model_api", None, "", ""))
    assert len(events) > 1 and all(len(event) == 6 for event in events)
    assert events[-1][1][-1]["role"] == "assistant"
    assert "测试模式回答" in events[-1][1][-1]["content"]


def test_gradio_registers_both_send_triggers_as_generators(client):
    config = client.get("/app/ai/config").json()
    for name, count in (("ai_console_send_stream", 6), ("floating_cli_chat_stream", 3)):
        callbacks = [item for item in config["dependencies"] if str(item.get("api_name", "")).startswith(name)]
        assert len(callbacks) == 2
        assert all(item["types"]["generator"] and len(item["outputs"]) == count for item in callbacks)
