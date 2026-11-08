"""Strict startup never announces readiness or auto-installs on invalid environments."""

import subprocess
import sys

import pytest

import start
from src.core import runtime_environment as runtime


def test_current_web_environment_passes_once():
    result = runtime.enforce_startup_runtime()
    assert result["passed"] and not result["external_distributions"]


def test_invalid_runtime_stops_launcher_before_uvicorn(tmp_path, monkeypatch):
    import src.core.config as config

    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "strict")
    monkeypatch.setattr(runtime, "inspect_runtime", lambda role: {"passed": False, "errors": ["wrong interpreter"]})
    monkeypatch.setattr(start, "_ensure_port_available", lambda *args: pytest.fail("must fail before port check"))
    config._SETTINGS = None
    try:
        with pytest.raises(SystemExit, match="环境不符合声明"):
            start.main([])
    finally:
        config._SETTINGS = None


def test_warn_is_explicit_and_invalid_modes_rejected(monkeypatch):
    monkeypatch.setattr(runtime, "inspect_runtime", lambda role: {"passed": False, "errors": ["fixture"]})
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "warn")
    assert runtime.enforce_startup_runtime()["mode"] == "warn"
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "off")
    with pytest.raises(SystemExit, match="strict / warn"):
        runtime.enforce_startup_runtime()


@pytest.mark.parametrize("args", [["start.py", "--help"], ["egs/entrypoints/cli.py", "system", "serve", "--help"]])
def test_help_does_not_require_startup(args):
    result = subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0 and "启动环境预检" not in result.stderr
