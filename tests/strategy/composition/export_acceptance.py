"""Preserve selected browser/API evidence and audit checks inside the project."""

import argparse
import ast
import json
from importlib.metadata import version

import requests
from loguru import logger

from src.core.config import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workshop-run", required=True)
    parser.add_argument("--resource-run", required=True)
    args = parser.parse_args()
    output = (PROJECT_ROOT / args.output).resolve()
    if not output.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Output must stay in this project")
    evidence = {}
    for name, run_id in (("browser_workshop", args.workshop_run), ("browser_resource_pool", args.resource_run)):
        response = requests.get(args.base_url + f"/api/v1/strategy-pipeline-runs/{run_id}", timeout=20)
        response.raise_for_status()
        envelope = response.json()
        row = envelope["data"]
        assert row["status"] == "finished" and row["result"]["is_mock"] is False
        result = row["result"]
        (output / (name + ".json")).write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        html = requests.get(args.base_url + f"/api/v1/strategy-pipeline-runs/{run_id}/files/report.html", timeout=20)
        html.raise_for_status()
        (output / (name + ".html")).write_bytes(html.content)
        if name == "browser_resource_pool":
            assert len(row["request"]["symbols"]) == 3
            assert all(stage["input_count"] <= 3 for stage in result["diagnostics"]["stages"])
            assert set(result["targets"]) <= set(row["request"]["symbols"])
        evidence[name] = {
            "run_id": run_id,
            "mode": row["request"]["mode"],
            "source": result["source"],
            "duration_ms": result["duration_ms"],
            "targets": result["targets"],
            "trade_count": result["metrics"].get("trade_count"),
        }
    source_roots = [
        "src/strategy/composition",
        "src/strategy/components",
        "src/engine/composition",
        "src/portfolio",
        "src/risk",
    ]
    files = [p for root in source_roots for p in (PROJECT_ROOT / root).glob("*.py")]
    functions = [
        (node.end_lineno - node.lineno + 1, str(path.relative_to(PROJECT_ROOT)), node.name)
        for path in files
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    encoding_files = files + [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "egs/config/strategies/strategy_components.yaml",
        PROJECT_ROOT / "docs/usage/strategy_composition.md",
        PROJECT_ROOT / "docs/principles/strategy_composition.md",
        PROJECT_ROOT / "doc/strategies/strategy_composition_risk_portfolio_design.md",
    ]
    encoding_errors = []
    for path in encoding_files:
        text = path.read_text(encoding="utf-8")
        if "\ufffd" in text or "???" in text:
            encoding_errors.append(str(path.relative_to(PROJECT_ROOT)))
    assert not encoding_errors, encoding_errors
    evidence.update(
        environment={
            key: version(key)
            for key in (
                "numpy",
                "pandas",
                "scikit-learn",
                "scipy",
                "lightgbm",
                "xgboost",
                "torch",
                "gradio",
                "json-repair",
            )
        },
        encoding_errors=encoding_errors,
        largest_functions=sorted(functions, reverse=True)[:8],
        largest_files=sorted(
            [(len(p.read_text(encoding="utf-8").splitlines()), str(p.relative_to(PROJECT_ROOT))) for p in files],
            reverse=True,
        )[:5],
    )
    (output / "final_checks.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved browser execution and final checks: {}", output)


if __name__ == "__main__":
    main()
