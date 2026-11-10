import sys
from pathlib import Path

import pytest
from loguru import logger

import gradio as gr
import src.core.logger as logger_module
from src.core.exceptions import BusinessError
from src.frontend.app import _callback_location, _safe
from src.frontend.services import FrontendService


def test_setup_logging_writes_structured_file_sink(tmp_path):
    logger.remove()
    logger_module._CONFIGURED = False

    logger_module.setup_logging(tmp_path, "INFO")
    app_logger = logger_module.get_logger("unit-test")
    app_logger.info("日志链路测试")

    logger.complete()
    log_files = list(tmp_path.glob("app_*.log"))
    assert log_files
    content = log_files[0].read_text(encoding="utf-8")
    assert "unit-test" in content
    assert "日志链路测试" in content

    logger.remove()
    logger_module._CONFIGURED = False


def test_log_format_is_plain_loguru_text():
    assert "<green>" not in logger_module.LOG_FORMAT
    assert "<level>" not in logger_module.LOG_FORMAT
    assert "{extra[channel]}" in logger_module.LOG_FORMAT
    assert "{extra[module]}" in logger_module.LOG_FORMAT
    assert "{name}:{function}:{line}" in logger_module.LOG_FORMAT
    assert "<level>" in logger_module.CONSOLE_LOG_FORMAT
    assert "<cyan>" in logger_module.CONSOLE_LOG_FORMAT


def test_log_messages_and_tracebacks_redact_credentials(monkeypatch):
    monkeypatch.setenv("UNIT_LOG_API_KEY", "synthetic-log-credential-12345")
    record = {"extra": {"api_key": "synthetic-log-credential-12345"}, "message": "request", "exception": None}
    try:
        raise ValueError("synthetic-log-credential-12345")
    except ValueError:
        record["exception"] = sys.exc_info()
    logger_module._ensure_module(record)
    assert "synthetic-log-credential-12345" not in str(record)
    assert "ValueError" in record["message"] and "<configured>" in record["message"]


def test_capture_stdout_routes_third_party_output_to_loguru():
    messages: list[str] = []
    sink_id = logger.add(
        lambda message: messages.append(str(message)), format="{extra[module]}|{message}", level="WARNING"
    )
    try:
        with logger_module.capture_stdout_to_loguru("stdout-test"):
            sys.stdout.write("new /app\n")
        logger.complete()
    finally:
        logger.remove(sink_id)

    joined = "\n".join(messages)
    assert "stdout-test|third-party stdout captured | new /app" in joined


def test_console_encoding_is_configured_as_utf8(monkeypatch):
    calls: list[dict[str, str]] = []

    class FakeStream:
        def reconfigure(self, **kwargs: str) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(sys, "stdout", FakeStream())
    monkeypatch.setattr(sys, "stderr", FakeStream())

    logger_module._configure_console_encoding()

    assert calls == [{"encoding": "utf-8", "errors": "replace"}, {"encoding": "utf-8", "errors": "replace"}]


def test_third_party_console_records_are_filtered():
    assert logger_module._should_emit({"extra": {"module": "uvicorn.error"}, "level": logger.level("ERROR")})
    assert not logger_module._should_emit({"extra": {"module": "uvicorn.error"}, "level": logger.level("WARNING")})
    assert not logger_module._should_emit({"extra": {"module": "uvicorn.error"}, "level": logger.level("INFO")})
    assert not logger_module._should_emit(
        {"extra": {"module": "urllib3.connectionpool"}, "level": logger.level("WARNING")}
    )
    assert logger_module._should_emit({"extra": {"module": "startup"}, "level": logger.level("INFO")})


def test_business_sources_do_not_use_print_calls():
    paths = [Path("start.py"), *Path("src").rglob("*.py")]
    offenders = [str(path) for path in paths if "print(" in path.read_text(encoding="utf-8")]

    assert offenders == []


def test_business_sources_do_not_use_stdlib_logging_calls():
    allowed = {Path("src/core/logger.py"), Path("src/data/provider_output.py")}
    paths = [Path("start.py"), *Path("src").rglob("*.py")]
    offenders = []
    for path in paths:
        if path in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "import logging" in text or "from logging" in text or "logging." in text or "pylogrus" in text:
            offenders.append(str(path))

    assert offenders == []


def test_gradio_stdout_capture_stays_debug_only():
    mounting_source = Path("src/frontend/mounting.py").read_text(encoding="utf-8")

    assert mounting_source.count('capture_stdout_to_loguru("frontend.gradio.stdout", level="DEBUG")') == 2


def test_gradio_callback_logs_business_execution_and_failure():
    service = FrontendService()
    operation, source = _callback_location(lambda: service.load_dashboard_layout())
    assert operation == "FrontendService.load_dashboard_layout"
    assert source.replace("\\", "/").startswith("src/frontend/service/dashboard.py:")
    direct_operation, direct_source = _callback_location(service.market_overview)
    assert direct_operation == "FrontendService.market_overview"
    assert direct_source.replace("\\", "/").startswith("src/frontend/service/market.py:")

    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)), format="{extra[module]}|{message}")
    try:
        assert _safe(lambda: "ready")() == "ready"

        def rejected():
            raise BusinessError(4001, "invalid input")

        with pytest.raises(gr.Error):
            _safe(rejected)()
        logger.complete()
    finally:
        logger.remove(sink_id)

    joined = "\n".join(messages)
    assert "frontend.callback|frontend action backend method started" in joined
    assert "frontend.callback|frontend action backend method finished" in joined
    assert "frontend.callback|frontend action backend method failed" in joined
    assert "operation_id=" in joined
    assert "backend_method=test_gradio_callback_logs_business_execution_and_failure.<locals>.rejected" in joined
    assert "source=tests" in joined and "test_logger.py:" in joined
    assert "error_type=BusinessError" in joined
