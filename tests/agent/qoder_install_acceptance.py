"""Inspect the installed official binary and one bounded native headless invocation."""

import json
import subprocess
from hashlib import sha256
from pathlib import Path

import yaml
from json_repair import loads as repair_json
from loguru import logger

from src.agent.qoder_cli import QoderCliRunner
from src.core.config import PROJECT_ROOT


def main():
    cfg = yaml.safe_load(
        Path(__file__).with_name("fixtures").joinpath("qoder_install.yaml").read_text(encoding="utf-8")
    )
    output = PROJECT_ROOT / cfg["output"]
    output.mkdir(parents=True, exist_ok=True)
    assert sha256(Path(cfg["archive"]).read_bytes()).hexdigest() == cfg["archive_sha256"]
    runner = QoderCliRunner(timeout_seconds=cfg["conversation_timeout_seconds"])
    inspected = {}
    for name, args in (
        ("version", ["--version"]),
        ("status", ["--setting-sources", "user", "status", "--output", "json"]),
    ):
        result = subprocess.run(
            [runner.executable(), *args],
            cwd=PROJECT_ROOT,
            env=runner.environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=cfg["metadata_timeout_seconds"],
        )
        inspected[name] = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    result = runner.run_once(cfg["prompt"])
    summary = {
        "installed": runner.executable(),
        "config_dir": runner.environment()["QODER_CONFIG_DIR"],
        "archive_sha256": cfg["archive_sha256"],
        "manifest_url": cfg["manifest_url"],
        "inspection": inspected,
        "login_status": repair_json(inspected["status"]["stdout"]),
        "conversation": {
            "status": result.status,
            "text": result.text,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "events": result.events,
        },
        "scope": "native_install_auth_and_one_hello_not_strategy_performance",
        "parameter_tuning": False,
    }
    (output / "acceptance.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Native Qoder verified; version={} logged_in={} headless={}",
        inspected["version"]["stdout"].strip(),
        summary["login_status"].get("logged_in"),
        result.status,
    )


if __name__ == "__main__":
    main()
