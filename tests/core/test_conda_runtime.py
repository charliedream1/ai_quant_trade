"""Conda environments preserve dependency and origin gates without requiring pyvenv.cfg."""

from pathlib import Path

import pytest
import yaml

from src.core.config import PROJECT_ROOT
from src.core.runtime_environment import _environment_errors, _installed_requirement


def policy(prefix: Path, **overrides):
    configuration = yaml.safe_load(
        (PROJECT_ROOT / "egs/config/operations/runtime_environments.yaml").read_text(encoding="utf-8")
    )
    return {**configuration["isolation"], "directory": str(prefix), **overrides}


def test_named_conda_environment_is_recognized_without_pyvenv(tmp_path):
    prefix = tmp_path / "envs" / "research"
    (prefix / "conda-meta").mkdir(parents=True)
    (prefix / "conda-meta/history").write_text("# isolated environment\n", encoding="utf-8")
    errors, inherited = _environment_errors(prefix, policy(tmp_path / "default-venv"), [3, 10])
    assert not errors and not inherited


@pytest.mark.parametrize("base_name", ["base", "anaconda3", "miniforge3"])
def test_conda_base_is_rejected(tmp_path, base_name):
    prefix = tmp_path / base_name
    (prefix / "conda-meta").mkdir(parents=True)
    (prefix / "conda-meta/history").write_text("# base environment\n", encoding="utf-8")
    assert any("base/root" in error for error in _environment_errors(prefix, policy(prefix), [3, 10])[0])


def test_explicit_environment_selection_is_not_bypassed_by_conda(tmp_path):
    prefix = tmp_path / "research"
    (prefix / "conda-meta").mkdir(parents=True)
    (prefix / "conda-meta/history").touch()
    errors, _ = _environment_errors(prefix, policy(tmp_path / "selected", explicit_directory=True), [3, 10])
    assert errors


def test_package_mismatch_and_external_origin_still_fail(tmp_path):
    _, mismatch = _installed_requirement("loguru==0.0.1", tmp_path)
    _, outside = _installed_requirement("loguru==0.7.3", tmp_path)
    assert mismatch and outside


def test_major_version_mismatch_is_marked_incompatible(tmp_path):
    row, message = _installed_requirement("loguru==1.0.0", tmp_path)
    assert row and not row["compatible"] and message
