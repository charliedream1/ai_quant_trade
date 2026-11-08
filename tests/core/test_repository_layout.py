"""Verify migration contracts rather than only checking that directories exist."""

from pathlib import Path

import pytest

from src.core.calendar_utils import split_hour_minutes, validate
from src.core.config import PROJECT_ROOT
from src.core.config_overrides import override_config
from src.core.env_file import env_status, save_env_value
from src.core.filesystem import clean_dirs, find_file, make_dirs
from src.core.operation_logging import addlog


def test_environment_status_matches_actual_process_precedence(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    save_env_value("LAYOUT_TEST_KEY", "file-value", target=path)
    monkeypatch.setenv("LAYOUT_TEST_KEY", "process-value")
    status = env_status("LAYOUT_TEST_KEY", target=path)
    assert status["source"] == "process"
    assert status["locations"] == ["process", ".env"]
    assert "process-value" not in status["masked_value"]


def test_override_preserves_input_and_handles_boolean_false():
    original = {"strategy": {"enabled": True, "count": 2}}
    result = override_config(original, ["strategy.enabled false", "strategy.count 7", "missing.count 3"])
    assert original == {"strategy": {"enabled": True, "count": 2}}
    assert result == {"strategy": {"enabled": False, "count": 7}}


def test_logging_adapter_preserves_failure_instead_of_exiting_successfully():
    @addlog()
    def fail():
        raise ValueError("expected operation failure")

    with pytest.raises(ValueError, match="expected operation failure"):
        fail()


def test_filesystem_helpers_and_root_removal_guard(tmp_path):
    folder = tmp_path / "nested"
    make_dirs(folder)
    path = folder / "fixture.txt"
    path.write_text("local fixture", encoding="utf-8")
    assert Path(find_file(tmp_path, "fixture")) == path
    with pytest.raises(ValueError, match="filesystem root"):
        clean_dirs(Path(tmp_path.anchor))


def test_date_helpers_remain_strict():
    validate("2024-02-29")
    with pytest.raises(ValueError):
        validate("2023-02-29")
    assert split_hour_minutes("09:30") == (9, 30)
    with pytest.raises(ValueError):
        split_hour_minutes("25:30")


def test_documentation_roots_are_independent_siblings():
    assert (PROJECT_ROOT / "doc").is_dir() and (PROJECT_ROOT / "docs").is_dir()
    assert not (PROJECT_ROOT / "docs/doc").exists()
    assert not (PROJECT_ROOT / "doc/docs").exists()


def test_old_tool_import_routes_to_owned_source_implementation():
    from tools.file_io.find_files import find_file as compatibility_find
    from tools.log.log_util import addlog as compatibility_logging

    assert compatibility_find is find_file and compatibility_logging is addlog
