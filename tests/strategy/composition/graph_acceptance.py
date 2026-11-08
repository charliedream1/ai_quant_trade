"""Archive real graph execution evidence and compare the UI/CLI calculation contract."""

import argparse
import ast
import json
import shutil
import sqlite3
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path

import requests
from loguru import logger

from src.core.config import PROJECT_ROOT
from src.strategy.composition.config import config, template
from src.strategy.composition.validation import compile_plan


def navigation_fixture():
    """Exercise the configured node limit at three navigation levels without execution."""
    leaf = template("rule_trend")
    component = leaf["nodes"][1]["component"]
    leaf["nodes"] = [
        {"id": f"step{i}", "component": component, "inputs": [f"step{i - 1}" if i else "universe"], "params": {}}
        for i in range(config()["defaults"]["max_nodes"])
    ]
    leaf["output"] = leaf["nodes"][-1]["id"]
    outer = template("multi_sleeve")
    outer["sleeves"] = [{"id": "leaf", "budget": 1.0, "definition": leaf}]
    root = deepcopy(outer)
    root["name"] = "导航性能验收（不执行交易）"
    root["sleeves"] = [{"id": "group", "budget": 1.0, "definition": outer}]
    compile_plan(root)
    return {"format": "aiquant-strategy-graph", "version": 1, "document": root, "layout": {}}


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Acceptance artifacts must stay inside this project")
    return path


def source_checks():
    component = PROJECT_ROOT / "src/frontend/components/strategy_graph"
    sources = [p for p in component.rglob("*") if p.is_file() and not {"node_modules", "__pycache__"} & set(p.parts)]
    sources += list((PROJECT_ROOT / "src/frontend/service").glob("*graph*.py"))
    sources += [
        PROJECT_ROOT / p
        for p in (
            "README.md",
            "egs/config/strategies/strategy_graph.yaml",
            "doc/strategies/gradio_visual_strategy_editor_design.md",
            "docs/usage/strategy_composition.md",
            "docs/principles/strategy_graph.md",
            "docs/usage/assets/screenshots/README.md",
        )
    ]
    functions, sizes = [], []
    for path in sources:
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text and "?" * 3 not in text, path
        sizes.append((len(text.splitlines()), path.relative_to(PROJECT_ROOT).as_posix()))
        if path.suffix == ".py":
            functions.extend(
                (node.end_lineno - node.lineno + 1, path.name, node.name)
                for node in ast.walk(ast.parse(text))
                if isinstance(node, ast.FunctionDef)
            )
    return {
        "utf8_files_checked": len(sources),
        "encoding_errors": [],
        "largest_python_functions": sorted(functions, reverse=True)[:5],
        "largest_files": sorted(sizes, reverse=True)[:6],
        "versions": {key: version(key) for key in ("gradio", "fastapi", "lightgbm", "torch", "scikit-learn")},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--browser-run", required=True)
    parser.add_argument("--cli-run", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--cancel-run")
    args = parser.parse_args()
    output, runtime = project_path(args.output), project_path(args.runtime)
    output.mkdir(parents=True, exist_ok=True)

    def get(path):
        response = requests.get(args.base_url.rstrip("/") + "/api/v1" + path, timeout=30)
        response.raise_for_status()
        envelope = response.json()
        assert envelope["code"] == 0, envelope
        return envelope["data"]

    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = {}
    for name, run_id in (("browser", args.browser_run), ("cli", args.cli_run)):
        row = get(f"/strategy-pipeline-runs/{run_id}")
        assert row["status"] == "finished" and not row["result"]["is_mock"]
        rows[name] = row
        save(name + "-run.json", row)
        save(name + "-nodes.json", get(f"/strategy-pipeline-runs/{run_id}/nodes"))
        save(name + "-events.json", get(f"/strategy-pipeline-runs/{run_id}/events"))
    assert rows["browser"]["version_id"] == rows["cli"]["version_id"]
    fields = ("metrics", "curve", "trades", "orders", "targets")
    equality = {key: rows["browser"]["result"][key] == rows["cli"]["result"][key] for key in fields}
    assert all(equality.values()), equality
    save("ui-cli-consistency.json", {"version_id": rows["browser"]["version_id"], "equal": equality})
    if args.cancel_run:
        cancelled = get(f"/strategy-pipeline-runs/{args.cancel_run}")
        assert cancelled["status"] == "cancelled", cancelled["status"]
        save("browser-cancelled-run.json", cancelled)
        save("browser-cancelled-events.json", get(f"/strategy-pipeline-runs/{args.cancel_run}/events"))
    # sqlite backup includes the current WAL; copying the DB file alone could lose published versions.
    with sqlite3.connect(runtime / "platform.db") as source, sqlite3.connect(output / "acceptance.db") as target:
        source.backup(target)
    for relative in ("models/pipelines", "pipeline_snapshots", "reports/pipelines/decisions"):
        source = runtime / "data" / relative
        if source.exists():
            shutil.copytree(source, output / "runtime-evidence" / relative, dirs_exist_ok=True)
    save("navigation-fixture.json", navigation_fixture())
    save("source-checks.json", source_checks())
    logger.info("UI/CLI metrics, curve, trades, orders and targets are identical; archived {}", output)


if __name__ == "__main__":
    main()
