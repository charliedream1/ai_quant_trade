"""Archive actual evidence and review changed files; never invokes a model or deletes files."""

import argparse
import ast
import json
import os
import shutil
import sqlite3
import subprocess
from hashlib import sha256
from pathlib import Path
from statistics import median
from time import perf_counter

import requests
import yaml
from dotenv import dotenv_values
from loguru import logger

from src.core.config import PROJECT_ROOT


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def changed_files():
    paths = set()
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
        paths.update(PROJECT_ROOT / name for name in result.stdout.splitlines())
    return sorted(path for path in paths if path.is_file() and path.resolve().is_relative_to(PROJECT_ROOT.resolve()))


def collect(cfg, temp, archive):
    for path in temp.iterdir():
        if path.is_file() and path.suffix in {".log", ".xml", ".json"}:
            destination = archive / "checks" / path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    shutil.copytree(temp / cfg["browser"], archive / "browser", dirs_exist_ok=True)
    shutil.copytree(temp / "semgrep", archive / "checks/semgrep", dirs_exist_ok=True)
    for name in cfg["screenshots"]:
        shutil.copy2(temp / cfg["browser"] / name, PROJECT_ROOT / "docs/usage/assets/screenshots" / name)
    real = temp / "real-runtime"
    for path in real.glob("*.json"):
        (archive / "real").mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, archive / "real" / path.name)
    shutil.copytree(real / "data/reports/agent_strategies", archive / "real/reports", dirs_exist_ok=True)
    with sqlite3.connect(real / "platform.db") as source:
        source.row_factory = sqlite3.Row
        runs = []
        for row in source.execute("SELECT * FROM agent_strategy_runs ORDER BY id"):
            run = dict(row)
            for key in ("config", "request", "evidence", "result"):
                run[key] = json.loads(run[key])
            events = [
                {**dict(event), "payload": json.loads(event["payload"])}
                for event in source.execute(
                    "SELECT * FROM agent_strategy_events WHERE run_id=? ORDER BY id", (row["id"],)
                )
            ]
            write(archive / "real" / ("run-" + str(row["id"]) + ".json"), {"run": run, "events": events})
            usage = {}
            for event in events:
                if event["kind"] == "llm_response":
                    for key, value in event["payload"].get("usage", {}).items():
                        if type(value) is int:
                            usage[key] = usage.get(key, 0) + value
            runs.append(
                {
                    "id": row["id"],
                    "recipe": row["recipe"],
                    "status": row["status"],
                    "usage": usage,
                    "requests": sum(event["kind"] == "llm_request" for event in events),
                    "responses": sum(event["kind"] == "llm_response" for event in events),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        write(archive / "real/usage-all-runs.json", runs)
        with sqlite3.connect(archive / "real/platform.db") as backup:
            source.backup(backup)
    with sqlite3.connect(temp / "browser-runtime/platform.db") as source:
        with sqlite3.connect(archive / "browser/platform.db") as backup:
            source.backup(backup)


def performance(cfg, archive):
    session = requests.Session()
    session.trust_env = False
    results = {}
    for name, endpoint in cfg["endpoints"].items():
        durations = []
        for _ in range(cfg["measurements"]):
            started = perf_counter()
            response = session.get(cfg["base_url"] + endpoint, timeout=cfg["timeout_seconds"])
            response.raise_for_status()
            assert response.json()["code"] == 0
            durations.append(round((perf_counter() - started) * 1000, 2))
        results[name] = {"milliseconds": durations, "median_ms": median(durations), "bytes": len(response.content)}
    write(
        archive / "performance.json", {"scope": "local_readonly_no_model_calls_no_before_after_causal_claim", **results}
    )


def review(archive):
    files = [path for path in changed_files() if not path.is_relative_to(archive)]
    texts = [path for path in files if path.suffix in {".py", ".yaml", ".yml", ".md", ".sql"}]
    issues, functions, lengths = [], [], []
    secrets = [
        value for key, value in dotenv_values("E:/.deepseek_env").items() if "KEY" in key and value and len(value) > 12
    ]
    for path in texts:
        text = path.read_text(encoding="utf-8")
        name = path.relative_to(PROJECT_ROOT).as_posix()
        if "\ufffd" in text or "?" * 3 in text or any(secret in text for secret in secrets):
            issues.append(name)
        lengths.append({"path": name, "lines": len(text.splitlines())})
        if path.suffix == ".py":
            functions.extend(
                {"path": name, "function": node.name, "lines": node.end_lineno - node.lineno + 1}
                for node in ast.walk(ast.parse(text))
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
    checks = {}
    for path in (archive / "checks/semgrep").glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        checks[path.name] = {"results": value.get("results", []), "errors": value.get("errors", [])}
    write(
        archive / "review.json",
        {
            "encoding_or_secret_issues": issues,
            "text_files": len(texts),
            "largest_changed_files": sorted(lengths, key=lambda row: -row["lines"])[:10],
            "largest_changed_functions": sorted(functions, key=lambda row: -row["lines"])[:10],
            "semgrep_files": len(checks),
            "semgrep_findings": sum(len(row["results"]) for row in checks.values()),
            "semgrep_errors": sum(len(row["errors"]) for row in checks.values()),
        },
    )
    assert not issues, "Encoding or credential exposure; paths recorded without values"
    assert all(not row["errors"] for row in checks.values())
    for path in archive.rglob("*"):
        if path.is_file() and path.suffix not in {".db", ".jpg"}:
            content = path.read_bytes()
            assert not any(secret.encode() in content for secret in secrets), "Credential found in archived evidence"
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
        "Acceptance archived; text_files={} semgrep_files={} encoding_or_secret_issues=0", len(texts), len(checks)
    )


def cleanup_scope(cfg, archive):
    names = [cfg["temporary"], "egs/" + cfg["temporary"]]
    names += [".tools/preview_jobs/" + name for name in cfg["office_jobs"]]
    targets = []
    for name in names:
        target = (PROJECT_ROOT / name).resolve()
        assert target.is_relative_to(PROJECT_ROOT.resolve()) and target != PROJECT_ROOT.resolve()
        if target.exists():
            scan = Path("//?/" + str(target)) if os.name == "nt" else target
            contents = [path for path in scan.rglob("*") if path.is_file()]
            targets.append(
                {"path": name, "files": len(contents), "bytes": sum(path.stat().st_size for path in contents)}
            )
    write(
        archive / "cleanup-scope.json",
        {
            "authorization": "pending_user_confirmation",
            "deleted": False,
            "targets": targets,
            "office_provenance": "11 jobs created 2026-10-28 11:50-11:54 within full-v2 11:43:29+1030s; exact IDs only",
            "preserved": [
                "formal_evidence",
                "usage_screenshots",
                "all_environments",
                "older_blocked_directories",
                "user_data",
            ],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--performance", action="store_true")
    parser.add_argument("--cleanup-scope", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(__file__).with_name("fixtures").joinpath("acceptance.yaml").read_text(encoding="utf-8"))
    temporary, destination = PROJECT_ROOT / cfg["temporary"], PROJECT_ROOT / cfg["archive"]
    destination.mkdir(parents=True, exist_ok=True)
    if args.collect:
        collect(cfg, temporary, destination)
    if args.performance:
        performance(cfg, destination)
    if args.cleanup_scope:
        cleanup_scope(cfg, destination)
    review(destination)
