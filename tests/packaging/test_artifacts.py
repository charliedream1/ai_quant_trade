"""Inspect the actual wheel/sdist metadata and resource boundaries before installation."""

import json
import os
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

ARTIFACTS = os.environ.get("AIQUANT_TEST_DIST")
pytestmark = pytest.mark.skipif(not ARTIFACTS, reason="Set AIQUANT_TEST_DIST to a built wheel/sdist directory")


def test_wheel_metadata_and_console_entries():
    with zipfile.ZipFile(next(Path(ARTIFACTS).glob("*.whl"))) as archive:
        metadata = BytesParser().parsebytes(
            archive.read(next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA")))
        )
        assert metadata["Name"] == "b001-all-in-one"
        assert SpecifierSet(metadata["Requires-Python"]) == SpecifierSet(">=3.10.1,<3.15")
        assert metadata["License-Expression"] == "Apache-2.0"
        for value in metadata.get_all("Requires-Dist"):
            specs = list(Requirement(value).specifier)
            assert len(specs) == 1 and specs[0].operator == "==" and "*" not in specs[0].version
        entries = archive.read(
            next(n for n in archive.namelist() if n.endswith(".dist-info/entry_points.txt"))
        ).decode()
        assert "aiquant = src.cli.app:main" in entries and "aiquant-server = src.startup:main" in entries


def test_wheel_required_resources_and_no_private_state():
    with zipfile.ZipFile(next(Path(ARTIFACTS).glob("*.whl"))) as archive:
        names = set(archive.namelist())
        assert {
            "src/core/database_schema.sql",
            "src/frontend/assets/workspace_routes.js",
            "src/frontend/components/strategy_graph/assets/graph.js",
            "src/_distribution/egs/config/cli/commands.yaml",
            "src/_distribution/mkdocs.platform.yml",
        } <= names
        for name in names:
            assert not any(
                part
                in {
                    ".env",
                    ".llm_env",
                    ".codex",
                    ".trae",
                    ".workbuddy",
                    "node_modules",
                    "__pycache__",
                    "audit",
                    ".tools",
                }
                for part in Path(name).parts
            )
            assert not name.endswith((".db", ".sqlite", ".sqlite3", ".pyc", ".pem", ".key"))
        assert "src/_distribution/egs/config/platform/config.yaml" not in names
        manifest = json.loads(archive.read("src/_distribution/manifest.json"))
        assert all("src/_distribution/" + name in names for name in manifest["files"])


def test_source_archive_is_self_contained_and_scoped():
    with tarfile.open(next(Path(ARTIFACTS).glob("*.tar.gz"))) as archive:
        names = archive.getnames()
        assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in names)
        logical = {name.split("/", 1)[1] for name in names if "/" in name}
        assert {
            "setup.py",
            "pyproject.toml",
            "src/core/database_schema.sql",
            "scripts/packaging/build_support.py",
            "egs/config/platform/distribution_resources.txt",
        } <= logical
        assert not any(
            part in {".git", ".env", "node_modules", "__pycache__", "audit", ".venv-secure"}
            for name in names
            for part in Path(name).parts
        )
