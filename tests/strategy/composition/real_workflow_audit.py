"""Opt-in real CLI/SSE acceptance using a checksummed, unmodified market archive."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import requests
import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    output = (PROJECT_ROOT / cfg["output"]).resolve()
    if not output.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError("Output must stay in this project")
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index, case in enumerate(cfg["cases"]):
        label = f"{index + 1:02d}-{case['template']}-{case['mode']}"
        command = [
            sys.executable,
            "egs/entrypoints/cli.py",
            "--base-url",
            cfg["base_url"],
            "--format",
            "json",
            "--require-real",
            "--deadline",
            str(cfg["timeout"]),
            "--read-timeout",
            str(cfg["timeout"]),
            "pipeline",
            "run",
            "--snapshot-id",
            cfg["snapshot_id"],
            "--start-date",
            cfg["start_date"],
            "--end-date",
            cfg["end_date"],
        ]
        for key, value in case.items():
            if key != "expected_error":
                command.extend(["--" + key.replace("_", "-"), str(value)])
        started = perf_counter()
        run = subprocess.run(
            command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=cfg["timeout"]
        )
        envelope = json.loads(run.stdout)
        (output / (label + ".json")).write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        row = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        result = row.get("result") or {}
        expected = case.get("expected_error")
        success = (
            expected in str(result.get("error"))
            if expected
            else run.returncode == 0 and row.get("status") == "finished" and result.get("is_mock") is False
        )
        if not expected and case["mode"] == "backtest":
            success = success and len(result.get("curve", {}).get("dates", [])) > 20
        if row.get("id") and row["status"] == "finished":
            response = requests.get(
                cfg["base_url"] + f"/api/v1/strategy-pipeline-runs/{row['id']}/files/report.html", timeout=30
            )
            response.raise_for_status()
            (output / (label + ".html")).write_bytes(response.content)
        summary = {
            "case": label,
            "success": success,
            "exit_code": run.returncode,
            "status": row.get("status"),
            "run_id": row.get("id"),
            "seconds": round(perf_counter() - started, 3),
            "metrics": result.get("metrics"),
            "validation": result.get("validation"),
            "decision_count": len(result.get("diagnostics", {}).get("decisions", [])),
            "error": result.get("error"),
            "stderr": run.stderr,
        }
        summaries.append(summary)
        (output / "summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("{} | passed={} status={} duration={}s", label, success, summary["status"], summary["seconds"])
    logger.info("Acceptance report: {}", output)
    return 0 if all(row["success"] for row in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
