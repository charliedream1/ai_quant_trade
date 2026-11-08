"""Offline parser, input precedence, policy and machine output contracts."""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.cli.catalog import commands
from src.cli.config import load_config
from src.cli.errors import CliError, ExitCode, result_exit
from src.cli.input import build_request
from src.cli.output import csv_text, redact
from src.cli.parser import parse
from src.cli.policy import check_policy, operation_target, resolve_operation

ROOT = Path(__file__).resolve().parents[2]


def test_existing_rest_operations_have_explicit_registered_mapping():
    registered = {
        (entry.get("method"), entry.get("path")) for entry in commands().values() if not entry.get("disabled")
    }
    existing = set()
    for path in (ROOT / "src/api/routes").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        prefix = next(
            (
                keyword.value.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "APIRouter"
                for keyword in node.keywords
                if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant)
            ),
            "",
        )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "router"
                and node.func.attr in {"get", "post", "put", "patch", "delete"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                existing.add((node.func.attr.upper(), prefix + node.args[0].value))
    # Native stream endpoints are selected by the regular command's stream_path.
    registered |= {
        (entry.get("method"), entry["stream_path"]) for entry in commands().values() if entry.get("stream_path")
    }
    assert len(existing & registered) / len(existing) >= 0.9
    assert len(registered) > 150


def test_global_flags_work_before_and_after_and_keep_zero_false(tmp_path):
    path = tmp_path / "request.yaml"
    path.write_text(
        "strategy_id: 1\ncommission_rate: 0.2\nparams: {model_params: {seed: 7, depth: 4}}\n", encoding="utf-8"
    )
    options, args, definition = parse(
        [
            "--format",
            "json",
            "backtest",
            "run",
            "--file",
            str(path),
            "--set",
            "params.model_params.depth=3",
            "--set",
            "params.enabled=false",
            "--commission-rate",
            "0",
            "--dry-run",
        ]
    )
    request = build_request(options, args, definition, 10000)
    assert options.format == "json"
    assert request["body"]["commission_rate"] == 0
    assert request["body"]["params"] == {"model_params": {"seed": 7, "depth": 3}, "enabled": False}


@pytest.mark.parametrize(
    "arguments",
    [
        ["backtest", "run", "--set", "stratgey_id=1"],
        ["backtest", "run", "--set", "params._experiment=1"],
        ["backtest", "run", "--start-date", "2026-99-01"],
        ["backtest", "run", "--set", "commission_rate=NaN"],
        ["news", "list", "--start-time", "2026-01-01"],
    ],
)
def test_invalid_request_never_reaches_transport(arguments):
    options, args, definition = parse(arguments)
    with pytest.raises(CliError):
        build_request(options, args, definition, 10000)


def test_generic_and_semantic_deletes_share_confirmation():
    options, args, definition = parse(["strategy", "delete", "42"])
    request = build_request(options, args, definition, 10000)
    _, generic_definition = resolve_operation("DELETE", "/strategies/42")
    for entry in (definition, generic_definition):
        with pytest.raises(CliError):
            check_policy(entry, request, options, {})


def test_live_risk_cannot_bypass_context_gate_through_generic_update():
    options, _, _ = parse(["system", "info"])
    _, definition = resolve_operation("PUT", "/live-configs/42")
    with pytest.raises(CliError, match="未启用"):
        check_policy(
            definition,
            {"method": "PUT", "path": "/live-configs/42", "body": {"risk_controls": {}}, "confirm_id": "42"},
            options,
            {"allow_live_actions": False},
        )
    assert operation_target(definition, "/live-configs/42", {}) == "42"
    _, start = resolve_operation("POST", "/live-runs")
    assert operation_target(start, "/live-runs", {"config_id": 42}) == "42"


def test_outcome_and_retrieval_have_distinct_exit_codes():
    result = {"code": 0, "message": "", "data": {"status": "blocked"}}
    assert result_exit(result) == 0
    assert result_exit(result, execution=True) == ExitCode.UNAVAILABLE
    assert result_exit({"code": 1002, "data": None}) == ExitCode.BUSINESS
    assert result_exit({"code": 0, "data": {"success": False}}, execution=True) == ExitCode.BUSINESS


def test_output_redacts_credentials_and_protects_csv_formula():
    assert redact({"headers": {"Authorization": "secret"}})["headers"]["Authorization"] == "***"
    assert "'=1+1" in csv_text([{"name": "=1+1", "pnl": -3}])


def test_help_is_offline_and_never_imports_gradio_or_database():
    source = "import sys; from src.cli.app import main; result=main(['--help']); assert 'gradio' not in sys.modules; assert 'src.core.database' not in sys.modules; raise SystemExit(result)"
    run = subprocess.run(
        [sys.executable, "-c", source], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20
    )
    assert run.returncode == 0, run.stderr
    assert "aiquant" in run.stdout
    assert "\x1b[" not in run.stdout


def test_source_entry_dry_run_is_valid_json_and_no_network():
    run = subprocess.run(
        [
            sys.executable,
            "egs/entrypoints/cli.py",
            "--base-url",
            "http://127.0.0.1:1",
            "backtest",
            "run",
            "--strategy-id",
            "1",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["data"]["body"] == {"strategy_id": 1}


def test_invalid_output_format_is_rejected_before_execution():
    options, _, _ = parse(["--format", "bad", "system", "info"])
    with pytest.raises(CliError):
        load_config(options)


def test_business_flags_do_not_become_global_abbreviations_or_command_name():
    options, args, definition = parse(["ai", "ask", "--session-id", "1", "--message", "hello"])
    assert options.message_file is None
    assert build_request(options, args, definition, 10000)["body"]["message"] == "hello"
    options, args, definition = parse(["mcp", "create", "--command", "mcp-executable"])
    assert build_request(options, args, definition, 10000)["body"]["command"] == "mcp-executable"
    options, args, definition = parse(
        ["--base-url", "http://localhost:8000", "model", "create", "--model-base-url", "http://localhost:9000/v1"]
    )
    assert options.base_url.endswith(":8000")
    assert build_request(options, args, definition, 10000)["body"]["base_url"].endswith(":9000/v1")
