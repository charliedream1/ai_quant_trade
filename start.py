"""Start the FastAPI, modular Gradio, REST API, and WebSocket service."""

from __future__ import annotations

import argparse
import os
import socket
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start AIQuant智投 service")
    parser.add_argument("--host", help="Listen host; defaults to config or ALL_IN_ONE_HOST")
    parser.add_argument("--port", type=int, help="Listen port; defaults to config or ALL_IN_ONE_PORT")
    parser.add_argument(
        "--log-level",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
        help="Application log level",
    )
    parser.add_argument("--reload", action="store_true", help="Reload the process when Python files change")
    return parser


def _ensure_port_available(host: str, port: int) -> None:
    """Fail fast before printing URLs when the configured port is occupied."""
    checked = False
    for family, socktype, proto, _, sockaddr in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        checked = True
        with socket.socket(family, socktype, proto) as sock:
            try:
                sock.bind(sockaddr)
            except OSError as exc:
                raise OSError(f"{host}:{port} is not available: {exc}") from exc
    if not checked:
        raise OSError(f"{host}:{port} is not available: address cannot be resolved")


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.host:
        os.environ["ALL_IN_ONE_HOST"] = args.host
    if args.port is not None:
        if not 1 <= args.port <= 65535:
            raise SystemExit("--port must be between 1 and 65535")
        os.environ["ALL_IN_ONE_PORT"] = str(args.port)
    if args.log_level:
        os.environ["ALL_IN_ONE_LOG_LEVEL"] = args.log_level.upper()

    os.chdir(PROJECT_ROOT)

    import uvicorn

    from src.core.config import get_settings
    from src.core.logger import get_logger, intercept_stdlib_logging, setup_logging
    from src.core.runtime_environment import enforce_startup_runtime

    settings = get_settings()
    setup_logging(settings.data_dir / "logs", settings.log_level)
    intercept_stdlib_logging()
    logger = get_logger("startup")
    enforce_startup_runtime()
    log_level = args.log_level or settings.log_level.lower()
    display_host = "127.0.0.1" if settings.host in ("0.0.0.0", "::") else settings.host
    try:
        _ensure_port_available(settings.host, settings.port)
    except OSError as exc:
        logger.error(
            "backend port occupied | host={} port={} error={} | 请释放端口或使用 --port 指定其他端口",
            settings.host,
            settings.port,
            exc,
        )
        raise SystemExit(1) from exc

    logger.info("backend port check passed | host={} port={}", settings.host, settings.port)
    logger.info(
        "backend runtime fingerprint | pid={} executable={} python={} cwd={} command={} project_root={}",
        os.getpid(),
        sys.executable,
        sys.version.split()[0],
        Path.cwd(),
        " ".join(sys.argv),
        PROJECT_ROOT,
    )
    logger.info("Gradio frontend: http://{}:{}/app/", display_host, settings.port)
    logger.info("Legacy Gradio during migration: http://{}:{}/legacy-app/", display_host, settings.port)
    logger.info("API docs: http://{}:{}/docs", display_host, settings.port)
    logger.info(
        "backend process launch | host={} port={} reload={} log_level={} data_dir={} db_path={}",
        settings.host,
        settings.port,
        args.reload,
        log_level.upper(),
        settings.data_dir,
        settings.db_path,
    )
    uvicorn.run(
        "src.api.app:app",
        host=settings.host,
        port=settings.port,
        log_level="warning",
        log_config=None,
        access_log=False,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
