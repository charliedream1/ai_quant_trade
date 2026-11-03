"""Business configuration and job workflows through the public CLI."""

import json
import subprocess
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

import requests

from src.cli.catalog import commands
from src.cli.client import Client
from src.cli.config import load_config
from src.cli.parser import parse

ROOT = Path(__file__).resolve().parents[2]


def test_jobs_skills_watchlist_and_models(cli_command):
    job = cli_command(
        "job", "create", "--name", "CLI-health", "--job-type", "system_health_check", "--enabled", "false"
    )["data"]["job_id"]
    assert cli_command("job", "show", job)["data"]["enabled"] == 0
    result = cli_command("job", "trigger", job)["data"]
    assert result["status"] == "成功"
    assert cli_command("job", "history", job)["data"]["items"]
    cli_command("job", "update", job, "--cron", "0 17 * * 1-5")
    cli_command("job", "enable", job)
    cli_command("job", "disable", job)
    group = cli_command("watchlist", "group", "create", "--name", "CLI-watch")["data"]["id"]
    cli_command("watchlist", "symbol", "add", group, "--symbols", "300750,600519")
    assert len(cli_command("watchlist", "quotes", "--group-id", group)["data"]) == 2
    skill = next(item for item in cli_command("skill", "list")["data"] if item["name"] == "news_summary")
    cli_command("skill", "enable", skill["skill_id"])
    cli_command("skill", "params", skill["skill_id"], "--set", "params.limit=3")
    assert cli_command("skill", "run", skill["skill_id"])["data"]["status"] == "success"
    cli_command("model", "chat", "--question", "hello", "--require-real", expected=7)
    cli_command("job", "delete", job, "--yes", "--confirm-id", job)


def test_live_actions_obey_context_and_existing_backend_validation(cli_command):
    strategy = cli_command(
        "strategy",
        "examples",
        "import",
        "--example",
        "egs/strategy_examples/dual_ma_strategy.py",
        "--name",
        "CLI-live-gate",
    )["data"]["strategy_id"]
    config = cli_command(
        "live",
        "config",
        "create",
        "--name",
        "CLI-gated",
        "--strategy-id",
        strategy,
        "--channel",
        "paper",
        "--capital",
        100000,
    )["data"]["config_id"]
    assert cli_command("live", "validation", config)["data"]
    cli_command("live", "run", "--config-id", config, "--yes", "--confirm-id", config, expected=6)
    cli_command(
        "api",
        "call",
        "--method",
        "POST",
        "--path",
        "/live-runs",
        "--set",
        f"config_id={config}",
        "--yes",
        "--confirm-id",
        config,
        expected=6,
    )
    cli_command("live", "risk", config, "--risk-controls", "{}", expected=6)
    cli_command("api", "call", "--method", "POST", "--path", "/cli-sessions", expected=6)


def test_query_overhead_and_coverage_audit(cli_command, tmp_path):
    # Backend elapsed time and process wall time are reported separately.
    wall = []
    backend = []
    for _ in range(5):
        started = perf_counter()
        result = cli_command("system", "info")
        wall.append(round((perf_counter() - started) * 1000, 2))
        backend.append(result["meta"]["elapsed_ms"])
    registered = [entry for entry in commands().values() if entry.get("path") and not entry.get("disabled")]
    options, _, _ = parse(["--base-url", cli_command.base_url, "system", "info"])
    direct_ms = []
    warm_ms = []
    transport = Client(load_config(options))
    session = requests.Session()
    session.trust_env = False
    try:
        for _ in range(5):
            started = perf_counter()
            assert session.get(cli_command.base_url + "/api/v1/system/info", timeout=5).json()["code"] == 0
            direct_ms.append(round((perf_counter() - started) * 1000, 2))
            started = perf_counter()
            assert transport.request({"method": "GET", "path": "/system/info", "query": {}, "body": {}})["code"] == 0
            warm_ms.append(round((perf_counter() - started) * 1000, 2))
    finally:
        transport.close()
        session.close()
    started = perf_counter()
    assert (
        subprocess.run([sys.executable, "egs/cli.py", "--help"], cwd=ROOT, capture_output=True, timeout=10).returncode
        == 0
    )
    help_ms = round((perf_counter() - started) * 1000, 2)
    report = {
        "kind": "cli_query_latency",
        "wall_ms": wall,
        "backend_ms": backend,
        "wall_median_ms": median(wall),
        "backend_median_ms": median(backend),
        "mapped_operations": len({(entry["method"], entry["path"]) for entry in registered}),
        "direct_api_ms": direct_ms,
        "warm_client_ms": warm_ms,
        "warm_extra_median_ms": round(median(warm_ms) - median(direct_ms), 2),
        "help_cold_ms": help_ms,
    }
    (tmp_path / "cli_performance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert median(backend) < 200
    assert median(warm_ms) - median(direct_ms) < 200
