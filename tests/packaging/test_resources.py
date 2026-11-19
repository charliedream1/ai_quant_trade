"""Package-resource selection and workspace initialization without a repository fallback."""

import json
import os
import subprocess
import sys
from pathlib import Path

from src import distribution_manifest as manifest

ROOT = Path(__file__).resolve().parents[2]


def test_required_assets_and_defaults_are_explicit():
    resources = {p.relative_to(ROOT).as_posix() for p in manifest.inventory()}
    assert {
        "src/core/database_schema.sql",
        "src/frontend/assets/workspace_routes.js",
        "src/frontend/components/strategy_graph/assets/graph.js",
        "egs/config/platform/distribution.yaml",
        "egs/config/ui/ui_translations.yaml",
        "egs/config/cli/commands.yaml",
        "mkdocs.platform.yml",
    } <= resources
    assert not any(
        part in {"node_modules", "__pycache__", ".env", ".codex", ".trae", ".workbuddy", "audit"}
        for name in resources
        for part in Path(name).parts
    )
    assert "egs/config/platform/config.yaml" not in resources


def test_unlisted_configuration_is_not_distributed(tmp_path, monkeypatch):
    (tmp_path / "public.yaml").write_text("public: true", encoding="utf-8")
    (tmp_path / "private.yaml").write_text("credential: fixture-only", encoding="utf-8")
    (tmp_path / "inventory.txt").write_text("public.yaml\n", encoding="utf-8")
    monkeypatch.setattr(manifest, "ROOT", tmp_path)
    monkeypatch.setattr(manifest, "POLICY", {**manifest.POLICY, "inventory": "inventory.txt"})
    assert [p.name for p in manifest.public_resources()] == ["public.yaml"]


def test_explicit_source_workspace_preserves_overrides_and_env(tmp_path):
    workspace = tmp_path / "workspace"
    override = workspace / "egs/config/platform/config.yaml"
    override.parent.mkdir(parents=True)
    override.write_text("port: 8127\ndata_dir: state\n", encoding="utf-8")
    (workspace / ".env").write_text("WORKSPACE_CANARY=fixture-only\n", encoding="utf-8")
    script = """import json,sys
from pathlib import Path
from src.core.config import Settings,PROJECT_ROOT
from src.core.paths import SOURCE_ROOT,project_file,relative_project_path
settings=Settings.load()
assert settings.port==8127
assert settings.data_dir==PROJECT_ROOT/'state'
assert settings.project_root==PROJECT_ROOT
assert (PROJECT_ROOT/'.env').read_text()=='WORKSPACE_CANARY=fixture-only\\n'
assert project_file('src/core/config.py')==SOURCE_ROOT/'src/core/config.py'
assert relative_project_path(project_file('src/core/config.py')).as_posix()=='src/core/config.py'
assert (PROJECT_ROOT/'egs/config/ui/navigation.yaml').is_file()
sys.stdout.write(json.dumps({'workspace':str(PROJECT_ROOT),'source':str(SOURCE_ROOT)}))
"""
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "ALL_IN_ONE_WORKSPACE": str(workspace),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for name in ("ALL_IN_ONE_DATA_DIR", "ALL_IN_ONE_PORT"):
        environment.pop(name, None)
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["workspace"] == str(workspace)
