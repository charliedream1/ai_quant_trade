"""Preserve dated execution, checks and market evidence without credentials."""

import argparse
import ast
import json
from hashlib import sha256
from importlib.metadata import Distribution, version
from pathlib import Path
from shutil import copy2, copytree

import requests
from loguru import logger

from src.core.config import PROJECT_ROOT


def contained(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    if not path.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Acceptance files must stay inside this project")
    return path


def save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--browser-report", required=True)
    parser.add_argument("--reference-browser")
    args = parser.parse_args()
    runtime, output = contained(args.runtime), contained(args.output)
    browser = json.loads(contained(args.browser_report).read_text(encoding="utf-8"))
    session = requests.Session()
    session.trust_env = False

    def get(path):
        response = session.get(args.base_url.rstrip("/") + "/api/v1" + path, timeout=30)
        response.raise_for_status()
        envelope = response.json()
        assert envelope["code"] == 0, envelope
        return envelope["data"]

    runs = {}
    versions = {
        version["id"]: version
        for row in get("/strategy-pipelines")
        for version in get(f"/strategy-pipelines/{row['id']}/versions")
    }
    for item in browser["results"]:
        assert item["passed"], item
        detail = item["detail"]
        for label, run_id in (("ui", detail["run_id"]), ("cli", detail.get("consistency", {}).get("cli"))):
            if not run_id or run_id in runs:
                continue
            row = get("/strategy-pipeline-runs/" + run_id)
            assert row["status"] == "finished" and row["result"]["is_mock"] is False
            save(output / "runs" / (run_id + ".json"), row)
            frozen = versions[row["version_id"]]
            save(output / "versions" / (str(frozen["id"]) + ".json"), frozen)
            save(output / "nodes" / (run_id + ".json"), get(f"/strategy-pipeline-runs/{run_id}/nodes"))
            if label == "ui":
                response = session.get(
                    args.base_url.rstrip("/") + f"/api/v1/strategy-pipeline-runs/{run_id}/files/report.html", timeout=30
                )
                response.raise_for_status()
                (output / "runs" / (run_id + ".html")).write_bytes(response.content)
            runs[run_id] = {"label": label, "version_id": row["version_id"], "metrics": row["result"]["metrics"]}
    for name in ("pipeline_snapshots", "models/pipelines"):
        source = runtime / name
        if source.is_dir():
            copytree(source, output / name, dirs_exist_ok=True)
    task = runtime.parent
    for name in (
        "full.xml",
        "review.xml",
        "final-full.xml",
        "factor-unit.xml",
        "factor-integration.xml",
        "portable-cache.xml",
        "optimized.xml",
        "docs-final.xml",
        "bandit-optimized.json",
        "bandit-review.json",
        "dependency-audit.json",
    ):
        source = task / name
        if source.is_file():
            (output / "checks").mkdir(parents=True, exist_ok=True)
            copy2(source, output / "checks" / name)
    copytree(task / "semgrep-native", output / "checks/semgrep-native", dirs_exist_ok=True)
    scanners = {
        item.metadata["Name"].lower(): item.version
        for item in Distribution.discover(path=[str(task / "security-tools")])
    }
    rules = task / "python-rules.yaml"
    save(
        output / "checks/security-tools.json",
        {
            "bandit": scanners["bandit"],
            "semgrep_native": scanners["semgrep"],
            "semgrep_rules_source": "https://semgrep.dev/c/p/python",
            "rules_sha256": sha256(rules.read_bytes()).hexdigest(),
            "rule_count": len(json.loads(rules.read_text(encoding="utf-8"))["rules"]),
            "metrics": "off",
        },
    )
    files = list((PROJECT_ROOT / "src/strategy/factors").glob("*.py"))
    files.extend(
        [
            PROJECT_ROOT / p
            for p in (
                "src/strategy/models/contracts.py",
                "src/strategy/models/features.py",
                "src/strategy/models/config.py",
                "src/strategy/components/models.py",
                "src/strategy/composition/runtime.py",
                "src/strategy/composition/validation.py",
                "src/strategy/composition/store.py",
                "src/engine/composition/factor_report.py",
                "src/engine/composition/report.py",
                "src/engine/composition/tree.py",
                "src/frontend/service/graph_evidence.py",
                "egs/factor_research.yaml",
                "doc/16_factor_research_pipeline_design.md",
                "docs/usage/factor_research.md",
                "docs/principles/factor_research.md",
            )
        ]
    )
    functions: list[list[int | str]] = []
    sizes: list[list[int | str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "\ufffd" not in text and "?" * 3 not in text and "？" * 3 not in text, path
        sizes.append([len(text.splitlines()), path.relative_to(PROJECT_ROOT).as_posix()])
        if path.suffix == ".py":
            functions.extend(
                [(node.end_lineno or node.lineno) - node.lineno + 1, path.name, node.name]
                for node in ast.walk(ast.parse(text))
                if isinstance(node, ast.FunctionDef)
            )
    save(
        output / "summary.json",
        {
            "runs": runs,
            "browser": browser,
            "largest_functions": sorted(functions, reverse=True)[:6],
            "largest_files": sorted(sizes, reverse=True)[:6],
            "utf8_checked": len(files),
            "versions": {name: version(name) for name in ("numpy", "pandas", "gradio", "lightgbm", "xgboost", "torch")},
        },
    )
    if args.reference_browser:
        reference_path = contained(args.reference_browser)
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        comparisons = []
        for previous, actual in zip(reference["results"][:3], browser["results"][:3], strict=True):
            old_id, new_id = previous["detail"]["run_id"], actual["detail"]["run_id"]
            old = json.loads((reference_path.parent / ("ui-run-" + old_id + ".json")).read_text(encoding="utf-8"))[
                "result"
            ]
            new = get("/strategy-pipeline-runs/" + new_id)["result"]
            same = {key: old[key] == new[key] for key in ("metrics", "curve", "trades", "orders", "targets")}
            old_research = old["diagnostics"].get("factor_diagnostics", {}).get("research", {}).get("research")
            new_research = new["diagnostics"].get("factor_diagnostics", {}).get("research", {}).get("research")
            same["research"] = old_research == new_research
            comparisons.append(
                {
                    "case": actual["name"],
                    "previous_run": old_id,
                    "optimized_run": new_id,
                    "equal": same,
                    "previous_ms": old["duration_ms"],
                    "optimized_ms": new["duration_ms"],
                }
            )
        save(output / "optimization-consistency.json", comparisons)
        assert all(all(row["equal"].values()) for row in comparisons), comparisons
    manifest = {
        p.relative_to(output).as_posix(): sha256(p.read_bytes()).hexdigest()
        for p in output.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }
    save(output / "manifest.json", manifest)
    logger.info("Preserved {} runs and {} artifacts at {}", len(runs), len(manifest), output)


if __name__ == "__main__":
    main()
