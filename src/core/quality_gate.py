"""Project-local quality entry usable from CI without changing parent-repo workflows."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="完整源码与安全语义质量门禁")
    parser.add_argument("--security-tests", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    destination = (args.output or PROJECT_ROOT / ".pytest_tmp" / ("quality-" + uuid4().hex)).resolve()
    if not destination.is_relative_to(PROJECT_ROOT):
        raise ValueError("质量报告必须保存在项目内")
    destination.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((PROJECT_ROOT / "egs/quality.yaml").read_text(encoding="utf-8"))
    commands = list(config["checks"])
    if args.security_tests:
        commands.append(
            [
                "pytest",
                *config["security_tests"],
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(destination / "pytest"),
            ]
        )
    results = []
    environment = os.environ.copy()
    environment.update(
        PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1",
        ALL_IN_ONE_HELP_DOCS_AUTO_BUILD="false",
        ALL_IN_ONE_DATA_DIR=str(destination / "data"),
        ALL_IN_ONE_DB_PATH=str(destination / "data/platform.db"),
    )
    for index, arguments in enumerate(commands):
        result = subprocess.run(
            [sys.executable, "-B", "-m", *arguments],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        (destination / f"{index:02}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        results.append({"check": arguments[0], "exit_code": result.returncode})
        logger.info("quality check | tool={} exit_code={}", arguments[0], result.returncode)
    (destination / "result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(any(row["exit_code"] for row in results))
