"""Preserve bounded acceptance evidence and verify UTF-8 without deleting user files."""

import ast
import json
import shutil
import socket
import sqlite3
import subprocess
from hashlib import sha256
from pathlib import Path

import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    cfg = yaml.safe_load(
        Path(__file__).with_name("fixtures").joinpath("qoder_install.yaml").read_text(encoding="utf-8")
    )
    temp = PROJECT_ROOT / cfg["output"]
    temp = temp.parent
    archive = PROJECT_ROOT / cfg["archive_output"]
    archive.mkdir(parents=True, exist_ok=True)
    for path in temp.iterdir():
        if path.is_file() and path.suffix in {".json", ".xml", ".log"}:
            (archive / "checks").mkdir(exist_ok=True)
            shutil.copy2(path, archive / "checks" / path.name)
    shutil.copytree(temp / cfg["browser_output"], archive / "browser", dirs_exist_ok=True)
    shutil.copytree(temp / "semgrep", archive / "checks/semgrep", dirs_exist_ok=True)
    shutil.copy2(temp / "native/acceptance.json", archive / "installation.json")
    for original, destination in (
        ("ai-console-light.jpg", "84-composer-workbench.jpg"),
        ("ai-chat-light.jpg", "85-composer-floating.jpg"),
        ("workbench-dark.jpg", "86-composer-dark.jpg"),
    ):
        shutil.copy2(
            temp / cfg["browser_output"] / original, PROJECT_ROOT / "docs/usage/assets/screenshots" / destination
        )
    with sqlite3.connect(temp / "browser-runtime/platform.db") as source:
        with sqlite3.connect(archive / "browser/platform.db") as backup:
            source.backup(backup)
        source.row_factory = sqlite3.Row
        write(
            archive / "browser/messages.json",
            [
                {**dict(row), "metadata": json.loads(row["metadata"])}
                for row in source.execute("SELECT * FROM ai_workspace_messages ORDER BY id")
            ],
        )
    files = set()
    for command in (
        ["diff", "--relative", "--name-only", "--", "."],
        ["ls-files", "--others", "--exclude-standard", "--", "."],
    ):
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", *command],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        files.update(PROJECT_ROOT / name for name in result.stdout.splitlines())
    files = sorted(path for path in files if path.is_file() and not path.is_relative_to(archive))
    lengths, functions, issues = [], [], []
    for path in files:
        if path.suffix not in {".py", ".md", ".yaml", ".js", ".css", ".example"}:
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if chr(0xFFFD) in text or "?" * 3 in text:
            issues.append(relative)
        lengths.append({"path": relative, "lines": len(text.splitlines())})
        if path.suffix == ".py":
            functions.extend(
                {"path": relative, "function": node.name, "lines": node.end_lineno - node.lineno + 1}
                for node in ast.walk(ast.parse(text))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    scans = [json.loads(path.read_text(encoding="utf-8-sig")) for path in (temp / "semgrep").glob("*.json")]
    probe = socket.socket()
    probe.settimeout(1)
    listening = probe.connect_ex(("127.0.0.1", 8899)) == 0
    probe.close()
    write(
        archive / "review.json",
        {
            "encoding_issues": issues,
            "semgrep_files": len(scans),
            "semgrep_errors": sum(len(row.get("errors", [])) for row in scans),
            "semgrep_findings": sum(len(row.get("results", [])) for row in scans),
            "largest_changed_files": sorted(lengths, key=lambda row: -row["lines"])[:6],
            "largest_changed_functions": sorted(functions, key=lambda row: -row["lines"])[:6],
            "listeners_8899": int(listening),
            "linux_tested": False,
        },
    )
    assert not issues and all(not row.get("errors") for row in scans)
    write(
        archive / "source-manifest.json",
        {path.relative_to(PROJECT_ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in files},
    )
    write(
        archive / "evidence-manifest.json",
        {
            path.relative_to(archive).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(archive.rglob("*"))
            if path.is_file() and path.name != "evidence-manifest.json"
        },
    )
    logger.info(
        "Qoder evidence archived; encoding issues={} source files={} listener={}", len(issues), len(files), listening
    )


if __name__ == "__main__":
    main()
