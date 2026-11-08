"""Record final review, source hashes, audit counts and project-bounded cleanup scope."""

import argparse
import ast
import hashlib
import json
from pathlib import Path

from loguru import logger

from src.core.config import PROJECT_ROOT

FILES = [
    "start.py",
    "src/main.py",
    "src/core/__init__.py",
    "src/core/runtime_environment.py",
    "src/agent/attachments.py",
    "src/agent/image_worker.py",
    "src/agent/image_validation.py",
    "src/agent/workspace.py",
    "src/agent/workspace_backend.py",
    "src/engine/insights/store.py",
    "src/frontend/common/navigation.py",
    "src/frontend/assets/workspace_routes.js",
    "src/frontend/shell.py",
    "src/frontend/theme.py",
    "src/frontend/features/knowledge.py",
    "src/frontend/features/simulation.py",
    "src/frontend/features/report_library.py",
    "src/frontend/service/report_library.py",
    "src/frontend/service/insights.py",
    "src/frontend/service/ai.py",
    "egs/config/operations/runtime_environments.yaml",
    "egs/config/models/image_validation.yaml",
    "egs/config/ui/navigation.yaml",
    "egs/config/platform/insight_reports.yaml",
    "egs/requirements/images.txt",
    "egs/requirements/images.lock.txt",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "README.md",
    "doc/ui/frontend_design.md",
    "doc/platform/api_design.md",
    "doc/ui/startup_attachment_navigation_report_design.md",
    "docs/usage/installation.md",
    "docs/usage/navigation_and_environment.md",
    "docs/usage/ai_workspace.md",
    "docs/usage/insight_reports.md",
    "docs/principles/runtime_navigation.md",
    "docs/audit/README.md",
    "docs/audit/startup_experience_2026-10-26/README.md",
    "docs/usage/assets/screenshots/README.md",
    "changelog/2026-10-W5.md",
    "tests/core/test_runtime_preflight.py",
    "tests/core/startup_experience_verification.py",
    "tests/core/startup_experience_archive.py",
    "tests/agent/test_image_attachments.py",
    "tests/frontend/test_report_library_resilience.py",
    "tests/frontend/test_workspace_routes.py",
    "tests/frontend/startup_experience_acceptance.py",
    "tests/frontend/startup_context_acceptance.py",
    "tests/frontend/test_gradio_frontend.py",
]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main(output, cleanup_status):
    source, encoding, structure = {}, [], []
    for name in FILES:
        path = PROJECT_ROOT / name
        content = path.read_text(encoding="utf-8-sig")
        issues = [marker for marker in ("\ufffd", "\u951f\u65a4\u62f7", "?" * 3) if marker in content]
        assert not issues, (name, issues)
        encoding.append({"path": name, "utf8": True, "mojibake_markers": issues})
        source[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix == ".py":
            tree = ast.parse(content)
            functions = [
                {"name": node.name, "lines": node.end_lineno - node.lineno + 1}
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
            structure.append(
                {
                    "path": name,
                    "lines": len(content.splitlines()),
                    "max_function": max(functions, key=lambda row: row["lines"], default={}),
                }
            )
    checks = output / "checks"
    write_json(output / "source-manifest.json", source)
    write_json(checks / "content-review.json", {"files": encoding, "python_structure": structure})
    semgrep = []
    for path in sorted((checks / "semgrep-final").glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8-sig"))
        assert not result.get("errors") and not result.get("results"), path
        semgrep.append(
            {"path": path.name, "findings": len(result.get("results", [])), "errors": len(result.get("errors", []))}
        )
    audits = {}
    for role in ("web", "image"):
        result = json.loads((checks / f"{role}-audit.json").read_text(encoding="utf-8"))
        audits[role] = {
            "packages": len(result["dependencies"]),
            "vulnerabilities": [
                {"name": row["name"], "version": row["version"], "count": len(row["vulns"])}
                for row in result["dependencies"]
                if row.get("vulns")
            ],
        }
    write_json(checks / "security-summary.json", {"audits": audits, "semgrep": semgrep})
    directories = [
        PROJECT_ROOT / ".pytest_tmp/startup-experience-20261026",
        PROJECT_ROOT / "egs/.pytest_tmp/startup-experience-20261026",
        PROJECT_ROOT / ".pytest_tmp/startup-experience-unit.log",
    ]
    cleanup = []
    for root in directories:
        resolved = root.resolve()
        assert resolved.is_relative_to(PROJECT_ROOT) and root.exists()
        files = [path for path in root.rglob("*") if path.is_file()] if root.is_dir() else [root]
        cleanup.append(
            {
                "path": str(resolved),
                "files": len(files),
                "bytes": sum(path.stat().st_size for path in files),
                "status": cleanup_status,
            }
        )
    write_json(output / "cleanup-scope.json", cleanup)
    artifacts = {
        str(path.relative_to(output)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in output.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(output / "manifest.json", artifacts)
    assert all(hashlib.sha256((output / name).read_bytes()).hexdigest() == digest for name, digest in artifacts.items())
    logger.info(
        "Evidence verified | artifacts={} source_files={} semgrep={} audits={} cleanup={}",
        len(artifacts),
        len(source),
        len(semgrep),
        audits,
        cleanup,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cleanup-status",
        choices=["awaiting_explicit_user_confirmation", "authorized_but_policy_blocked"],
        default="awaiting_explicit_user_confirmation",
    )
    args = parser.parse_args()
    main(args.output, args.cleanup_status)
