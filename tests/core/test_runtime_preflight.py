"""Strict startup never announces readiness or auto-installs on invalid environments."""

import subprocess
import sys
from types import SimpleNamespace

import pytest

import start
from src.core import runtime_environment as runtime


def test_current_web_environment_passes_once(monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_WEB_ENVIRONMENT", sys.prefix)
    result = runtime.enforce_startup_runtime()
    assert result["passed"] and not result["external_distributions"]


def test_runtime_version_gate_rejects_obsolete_patch_and_future_minor(monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_WEB_ENVIRONMENT", sys.prefix)
    monkeypatch.setattr(runtime.sys, "version_info", (3, 10, 0))
    assert "Python is below the supported baseline" in runtime.inspect_runtime()["errors"]
    monkeypatch.setattr(runtime.sys, "version_info", (3, 15, 0))
    assert "Python exceeds the verified support range" in runtime.inspect_runtime()["errors"]


def test_invalid_runtime_stops_launcher_before_uvicorn(tmp_path, monkeypatch):
    import src.core.config as config

    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "strict")
    monkeypatch.setattr(runtime, "inspect_runtime", lambda role: {"passed": False, "errors": ["wrong interpreter"]})
    monkeypatch.setattr(start, "_ensure_port_available", lambda *args: pytest.fail("must fail before port check"))
    config._SETTINGS = None
    try:
        with pytest.raises(SystemExit, match="Runtime requirements are incomplete"):
            start.main([])
    finally:
        config._SETTINGS = None


def test_missing_dependency_is_not_bypassed_by_legacy_warn(monkeypatch):
    monkeypatch.setattr(runtime, "inspect_runtime", lambda role: {"passed": False, "errors": ["fixture"]})
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "warn")
    with pytest.raises(SystemExit, match="Runtime requirements are incomplete"):
        runtime.enforce_startup_runtime()
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "off")
    with pytest.raises(SystemExit, match="strict / non-strict"):
        runtime.enforce_startup_runtime()


@pytest.mark.parametrize("mode, passed", [("strict", False), ("non-strict", True), ("warn", True)])
def test_version_and_origin_differences_follow_selected_policy(monkeypatch, tmp_path, mode, passed):
    monkeypatch.setenv("ALL_IN_ONE_WEB_ENVIRONMENT", sys.prefix)
    monkeypatch.setattr(runtime, "_requirements", lambda cfg: ["loguru==0.0.1"])
    result = runtime.inspect_runtime(mode=mode)
    assert result["passed"] is passed
    assert bool(result["warnings"]) is passed
    assert result["mode"] == ("non-strict" if mode == "warn" else mode)


@pytest.mark.parametrize("mode", ["strict", "non-strict"])
def test_missing_dependency_blocks_both_policies(monkeypatch, mode):
    monkeypatch.setenv("ALL_IN_ONE_WEB_ENVIRONMENT", sys.prefix)
    monkeypatch.setattr(runtime, "_requirements", lambda cfg: ["aqt-missing-runtime-fixture==1.0.0"])
    result = runtime.inspect_runtime(mode=mode)
    assert not result["passed"] and result["errors"]


def test_explicit_mode_overrides_environment_and_dotenv(monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", "strict")
    monkeypatch.setattr(runtime, "dotenv_values", lambda path: {"ALL_IN_ONE_RUNTIME_MODE": "warn"})
    config = {"startup": {"mode": "non-strict"}}
    assert runtime._runtime_mode(config) == "strict"
    assert runtime._runtime_mode(config, "non-strict") == "non-strict"
    monkeypatch.delenv("ALL_IN_ONE_RUNTIME_MODE")
    assert runtime._runtime_mode(config) == "non-strict"


def test_repository_defaults_to_non_strict_without_local_overrides(monkeypatch):
    monkeypatch.delenv("ALL_IN_ONE_RUNTIME_MODE", raising=False)
    monkeypatch.setenv("ALL_IN_ONE_WEB_ENVIRONMENT", sys.prefix)
    monkeypatch.setattr(runtime, "dotenv_values", lambda path: {})
    monkeypatch.setattr(runtime, "_requirements", lambda cfg: ["loguru==0.0.1"])
    report = runtime.enforce_startup_runtime()
    assert report["mode"] == "non-strict"
    assert report["passed"] and report["warnings"]


def test_non_strict_editable_environment_location_is_a_warning(monkeypatch):
    message = "Interpreter does not match the configured role environment"
    monkeypatch.setattr(runtime, "_environment_errors", lambda *args: ([message], False))
    monkeypatch.setattr(runtime, "_requirements", lambda cfg: [])
    relaxed = runtime.inspect_runtime(mode="non-strict")
    strict = runtime.inspect_runtime(mode="strict")
    assert relaxed["passed"] and message in relaxed["warnings"]
    assert not strict["passed"] and message in strict["errors"]


def test_installed_worker_environment_keeps_its_configured_location(tmp_path, monkeypatch):
    prefix = tmp_path / "other-worker"
    prefix.mkdir()
    (prefix / "pyvenv.cfg").write_text("include-system-site-packages = false\n", encoding="utf-8")
    monkeypatch.setattr(runtime, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runtime, "INSTALLED", True)
    policy = {"directory": "configured-worker", "project_dependencies": False, "allow_conda": False}
    errors, _ = runtime._environment_errors(prefix, policy, [3, 10, 1])
    assert "Interpreter does not match the configured role environment" in errors
    errors, _ = runtime._environment_errors(prefix, {**policy, "project_dependencies": True}, [3, 10, 1])
    assert not errors


def test_source_metadata_is_distinct_from_foreign_distributions(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "INSTALLED", False)
    monkeypatch.setattr(runtime, "RESOURCE_ROOT", tmp_path / "source")
    own = SimpleNamespace(metadata={"Name": "b001-all-in-one"}, locate_file=lambda _: tmp_path / "source")
    foreign = SimpleNamespace(metadata={"Name": "foreign-plugin"}, locate_file=lambda _: tmp_path / "foreign")
    monkeypatch.setattr(runtime.metadata, "distributions", lambda: [own, foreign])
    monkeypatch.setattr(runtime, "_requirements", lambda cfg: [])
    monkeypatch.setattr(runtime, "_environment_errors", lambda *args: ([], False))
    report = runtime.inspect_runtime(mode="strict")
    assert report["external_distributions"] == ["foreign-plugin"]
    assert not report["passed"]


@pytest.mark.parametrize("mode", ["strict", "non-strict"])
def test_start_launcher_applies_policy_before_server_dispatch(monkeypatch, tmp_path, mode):
    import uvicorn

    import src.core.config as config

    monkeypatch.setenv("ALL_IN_ONE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ALL_IN_ONE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ALL_IN_ONE_WEB_ENVIRONMENT", sys.prefix)
    monkeypatch.setenv("ALL_IN_ONE_RUNTIME_MODE", mode)
    monkeypatch.setattr(runtime, "_requirements", lambda cfg: ["loguru==0.0.1"])
    calls = []
    monkeypatch.setattr(start, "_ensure_port_available", lambda *args: calls.append("port"))
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append("server"))
    config._SETTINGS = None
    try:
        if mode == "strict":
            with pytest.raises(SystemExit):
                start.main([])
            assert calls == []
        else:
            start.main([])
            assert calls == ["port", "server"]
    finally:
        config._SETTINGS = None


@pytest.mark.parametrize("args", [["start.py", "--help"], ["egs/entrypoints/cli.py", "system", "serve", "--help"]])
def test_help_does_not_require_startup(args):
    result = subprocess.run([sys.executable, "-B", *args], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0 and "Runtime preflight" not in result.stderr
