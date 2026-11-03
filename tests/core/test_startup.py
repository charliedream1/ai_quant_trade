import socket

import pytest

import start


def _unused_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_startup_port_check_passes_for_free_port():
    start._ensure_port_available("127.0.0.1", _unused_port())


def test_startup_exits_before_printing_urls_when_port_is_occupied(tmp_path, monkeypatch):
    logged_messages: list[str] = []

    class FakeLogger:
        def info(self, message: str, *args: object) -> None:
            logged_messages.append(message.format(*args))

        def error(self, message: str, *args: object) -> None:
            logged_messages.append(message.format(*args))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen()
        port = int(blocker.getsockname()[1])

        monkeypatch.setenv("ALL_IN_ONE_HOST", "127.0.0.1")
        monkeypatch.setenv("ALL_IN_ONE_PORT", str(port))
        monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "all_in_one.db"))
        monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "mock")

        import uvicorn

        import src.core.config as config_module
        import src.core.logger as logger_module

        config_module._SETTINGS = None
        monkeypatch.setattr(logger_module, "setup_logging", lambda *args: None)
        monkeypatch.setattr(logger_module, "intercept_stdlib_logging", lambda: None)
        monkeypatch.setattr(logger_module, "get_logger", lambda name: FakeLogger())
        monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: pytest.fail("uvicorn.run should not be called"))
        try:
            with pytest.raises(SystemExit) as exc_info:
                start.main([])
        finally:
            config_module._SETTINGS = None

    assert exc_info.value.code == 1
    assert any("backend port occupied" in message for message in logged_messages)
    assert not any("Frontend:" in message for message in logged_messages)
