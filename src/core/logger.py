"""Loguru setup.

业务代码统一使用 ``from src.core.logger import get_logger``。
uvicorn 等基于标准库 logging 的组件通过 :class:`InterceptHandler`
桥接到 loguru，保证全系统只有一套日志格式与落盘策略。
"""

import logging
import sys
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from loguru import logger

from src.core.redaction import redact, redact_text

_CONFIGURED = False
_INTERCEPTED = False
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[channel]} | {extra[module]} | "
    "{name}:{function}:{line} | {message}"
)
CONSOLE_LOG_FORMAT = (
    "<dim>{time:YYYY-MM-DD HH:mm:ss.SSS}</dim> | <level>{level: <8}</level> | "
    "<cyan>{extra[channel]}</cyan> | <blue>{extra[module]}</blue> | "
    "<white>{name}:{function}:{line}</white> | <level>{message}</level>"
)
STDLIB_LOGGER_NAMES = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "httpx",
    "httpcore",
    "urllib3",
    "numexpr",
)
THIRD_PARTY_LOGGER_PREFIXES = ("uvicorn", "httpx", "httpcore", "urllib3", "numexpr")
QUIET_STDLIB_LOGGERS = set(STDLIB_LOGGER_NAMES)


def _log_channel(module: str) -> str:
    if module == "backend.http":
        return "http"
    if module.startswith(THIRD_PARTY_LOGGER_PREFIXES):
        return "third_party"
    if module.endswith(".stdout"):
        return "stdout_capture"
    return "business"


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def _ensure_module(record: Any) -> None:
    module = str(record["extra"].setdefault("module", "app"))
    record["extra"].setdefault("channel", _log_channel(module))
    record["extra"] = redact(record["extra"])
    text = record["message"]
    exception = record.get("exception")
    if exception:
        # Format without local variables, then redact the complete exception text.
        text += "\n" + "".join(traceback.format_exception(*exception))
        record["exception"] = None
    record["message"] = redact_text(text)


def _should_emit_console(record: Any) -> bool:
    module = str(record["extra"].get("module") or "")
    channel = str(record["extra"].get("channel") or _log_channel(module))
    if channel == "third_party" and record["level"].no < logger.level("ERROR").no:
        return False
    if module in QUIET_STDLIB_LOGGERS and record["level"].no < logger.level("ERROR").no:
        return False
    return True


def _should_emit_file(record: Any) -> bool:
    return True


def _should_emit(record: Any) -> bool:
    """Backward-compatible alias used by existing tests."""
    return _should_emit_console(record)


class InterceptHandler(logging.Handler):
    """Route standard-library logging records (e.g. uvicorn) into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        def patch_source(loguru_record: Any) -> None:
            loguru_record["name"] = record.name
            loguru_record["function"] = record.funcName
            loguru_record["line"] = record.lineno

        logger.patch(patch_source).opt(exception=record.exc_info).bind(module=record.name).log(
            level,
            record.getMessage(),
        )


class LoguruStdout:
    """File-like stdout sink that turns third-party prints into loguru records."""

    def __init__(self, module: str, level: str = "WARNING") -> None:
        self._log = get_logger(module)
        self._level = level.upper()
        self._buffer = ""

    def write(self, message: str) -> int:
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)
        return len(message)

    def flush(self) -> None:
        if self._buffer:
            self._emit(self._buffer)
            self._buffer = ""

    def _emit(self, line: str) -> None:
        text = line.strip()
        if text:
            self._log.log(self._level, "third-party stdout captured | {}", text[:1000])


def setup_logging(log_dir: Path | None = None, level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _configure_console_encoding()
    normalized_level = level.upper()
    logger.remove()
    logger.configure(patcher=_ensure_module)
    logger.add(
        sys.stderr,
        level=normalized_level,
        format=CONSOLE_LOG_FORMAT,
        filter=_should_emit_console,
        enqueue=True,
        colorize=True,
        backtrace=False,
        diagnose=False,
    )
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            level=normalized_level,
            encoding="utf-8",
            format=LOG_FORMAT,
            filter=_should_emit_file,
            enqueue=True,
            colorize=False,
            backtrace=False,
            diagnose=False,
        )
    _CONFIGURED = True


def startup_banner(
    log: Any,
    *,
    app_name: str,
    web_url: str,
    api_url: str,
    health_url: str,
    github_url: str,
    gitee_url: str,
) -> None:
    """Emit a compact colored startup logo and clickable-looking destinations."""
    logo = (
        "<cyan>╭──────────────────────────────╮</cyan>\n"
        f"<cyan>│</cyan> <bold><green>{app_name}</green></bold><cyan>              │</cyan>\n"
        "<cyan>│</cyan> <white>Quant Research · AI · Trade</white><cyan> │</cyan>\n"
        "<cyan>╰──────────────────────────────╯</cyan>"
    )
    log.opt(colors=True).info(logo)
    log.opt(colors=True).info(
        "<bold><green>启动成功</green></bold> | Web <u><blue>{}</blue></u> | API <u><blue>{}</blue></u> | Health <u><blue>{}</blue></u>",
        web_url,
        api_url,
        health_url,
    )
    log.opt(colors=True).info(
        "项目链接 | GitHub <u><blue>{}</blue></u> | Gitee <u><blue>{}</blue></u>",
        github_url,
        gitee_url,
    )


def intercept_stdlib_logging() -> None:
    """Redirect every standard-library logger into loguru exactly once."""
    global _INTERCEPTED
    if _INTERCEPTED:
        return
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in STDLIB_LOGGER_NAMES:
        stdlib_logger = logging.getLogger(name)
        stdlib_logger.handlers = []
        stdlib_logger.propagate = True
        stdlib_logger.setLevel(logging.WARNING)
    _INTERCEPTED = True


def get_logger(name: str = "app"):
    return logger.bind(module=name)


@contextmanager
def capture_stdout_to_loguru(module: str = "thirdparty.stdout", level: str = "WARNING") -> Iterator[None]:
    """Capture temporary third-party stdout writes and emit them via loguru."""
    original_stdout = sys.stdout
    capture = LoguruStdout(module, level)
    sys.stdout = capture
    try:
        yield
    finally:
        capture.flush()
        sys.stdout = original_stdout
