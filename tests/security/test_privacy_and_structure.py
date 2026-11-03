"""Semantic guards protect tracked secrets and important dependency boundaries."""

import ast
import subprocess

from src.core.config import PROJECT_ROOT


def test_git_index_does_not_track_runtime_credentials():
    result = subprocess.run(
        ["git", "ls-files", "--", ".env", ".llm_env", ".secrets"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert not result.stdout.strip()


def test_frontend_callbacks_do_not_import_http_routes():
    violations = []
    for path in (PROJECT_ROOT / "src/frontend").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src.api"):
                violations.append(str(path.relative_to(PROJECT_ROOT)))
    assert not violations


def test_shared_model_selection_is_independent_from_alpha_family():
    source = (PROJECT_ROOT / "src/agent/providers/contracts.py").read_text(encoding="utf-8")
    assert "src.alpha_mining" not in source
