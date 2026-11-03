"""Preserve completed validation, measure read-only calls and verify current text assets."""

import argparse
import ast
import json
import shutil
import socket
import sqlite3
import subprocess
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter

import requests
import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def archive(cfg, measure):
    temp, output = PROJECT_ROOT / cfg["temporary"], PROJECT_ROOT / cfg["archive"]
    output.mkdir(parents=True, exist_ok=True)
    checks = output / "checks"
    checks.mkdir(exist_ok=True)
    for path in temp.iterdir():
        if path.is_file() and path.suffix in {".xml", ".log", ".json"}:
            shutil.copy2(path, checks / path.name)
    shutil.copytree(temp / "semgrep", checks / "semgrep", dirs_exist_ok=True)
    shutil.copytree(temp / cfg["browser"], output / "browser", dirs_exist_ok=True)
    for name in cfg["screenshots"]:
        shutil.copy2(temp / cfg["browser"] / name, PROJECT_ROOT / "docs/usage/assets/screenshots" / name)
    with sqlite3.connect(temp / cfg["runtime"] / "platform.db") as source:
        with sqlite3.connect(output / "browser/platform.db") as destination:
            source.backup(destination)
        source.row_factory = sqlite3.Row
        write(
            output / "browser/notifications.json",
            [dict(row) for row in source.execute("SELECT * FROM notifications ORDER BY id")],
        )
    destination.close()
    source.close()
    if measure:
        session = requests.Session()
        session.trust_env = False
        results = {}
        for name, endpoint in (("config", "/config"), ("feed", "?client_id=" + cfg["client"])):
            durations = []
            for _ in range(cfg["measurements"]):
                started = perf_counter()
                response = session.get(
                    cfg["base_url"] + "/api/v1/notifications" + endpoint, timeout=cfg["timeout_seconds"]
                )
                response.raise_for_status()
                assert response.json()["code"] == 0
                durations.append(round((perf_counter() - started) * 1000, 2))
            results[name] = {"milliseconds": durations, "median_ms": median(durations), "bytes": len(response.content)}
        write(
            output / "performance.json",
            {"scope": "local_readonly_after_UI_fixture_no_prechange_causal_claim", **results},
        )
    files = set()
    for arguments in (
        ["diff", "--relative", "--name-only", "--", "."],
        ["ls-files", "--others", "--exclude-standard", "--", "."],
    ):
        result = subprocess.run(
            ["git", "-c", "core.quotepath=false", *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        files.update(PROJECT_ROOT / name for name in result.stdout.splitlines())
    files = sorted(
        path
        for path in files
        if path.is_file()
        and path.resolve().is_relative_to(PROJECT_ROOT.resolve())
        and not path.is_relative_to(PROJECT_ROOT / "docs/audit")
    )
    issues, functions = [], []
    for path in files:
        if path.suffix not in {".py", ".md", ".yaml", ".yml", ".js", ".css", ".svg", ".sql"}:
            continue
        text = path.read_text(encoding="utf-8")
        if chr(0xFFFD) in text or "?" * 3 in text:
            issues.append(path.relative_to(PROJECT_ROOT).as_posix())
        if path.suffix == ".py":
            functions.extend(
                {
                    "path": path.relative_to(PROJECT_ROOT).as_posix(),
                    "function": node.name,
                    "lines": node.end_lineno - node.lineno + 1,
                }
                for node in ast.walk(ast.parse(text))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    scans = [json.loads(path.read_text(encoding="utf-8-sig")) for path in (checks / "semgrep").glob("*.json")]
    probe = socket.socket()
    probe.settimeout(1)
    listening = probe.connect_ex(("127.0.0.1", 8890)) == 0
    probe.close()
    write(
        output / "review.json",
        {
            "encoding_issues": issues,
            "source_files": len(files),
            "semgrep_files": len(scans),
            "semgrep_errors": sum(len(row.get("errors", [])) for row in scans),
            "semgrep_findings": sum(len(row.get("results", [])) for row in scans),
            "largest_changed_functions": sorted(functions, key=lambda row: -row["lines"])[:8],
            "listener_8890": int(listening),
            "linux_tested": False,
        },
    )
    assert not issues and all(not row.get("errors") for row in scans)
    write(
        output / "source-manifest.json",
        {path.relative_to(PROJECT_ROOT).as_posix(): sha256(path.read_bytes()).hexdigest() for path in files},
    )
    write(
        output / "evidence-manifest.json",
        {
            path.relative_to(output).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.rglob("*"))
            if path.is_file() and path.name != "evidence-manifest.json"
        },
    )
    logger.info(
        "Notification evidence archived; text issues={} source files={} listening={}",
        len(issues),
        len(files),
        listening,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--measure", action="store_true")
    args = parser.parse_args()
    values = yaml.safe_load(Path(__file__).with_name("acceptance.yaml").read_text(encoding="utf-8"))
    archive(values, args.measure)
