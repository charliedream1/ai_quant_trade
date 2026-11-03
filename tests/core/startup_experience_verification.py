"""Reproducible real-process checks and latency evidence for design 21."""

import argparse
import io
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

import requests
from loguru import logger
from PIL import Image

from src.agent.attachments import prepare_attachments
from src.core.config import PROJECT_ROOT
from src.core.runtime_environment import enforce_startup_runtime


def invoke(command, **kwargs):
    started = perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60, **kwargs)
    return {
        "command": command,
        "code": result.returncode,
        "seconds": perf_counter() - started,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main(base, output):
    output.mkdir(parents=True, exist_ok=True)
    results = {"runtime": [enforce_startup_runtime() for _ in range(3)]}
    assert all(row["passed"] for row in results["runtime"])
    picture = io.BytesIO()
    Image.new("RGB", (640, 480), "navy").save(picture, "PNG")
    images = [output / f"研究图-{index}.png" for index in range(8)]
    for path in images:
        path.write_bytes(picture.getvalue())
    text = output / "文本说明.md"
    text.write_text("明确测试样本，未调用真实模型。", encoding="utf-8")
    timings = {}
    for name, files in (("text", [text]), ("one_image", images[:1]), ("eight_images", images)):
        elapsed = []
        for _ in range(3):
            started = perf_counter()
            prepare_attachments(files)
            elapsed.append((perf_counter() - started) * 1000)
        timings[name] = {"ms": elapsed, "median_ms": median(elapsed)}
    results["attachment_timings"] = timings
    fake = output / "renamed.jpg"
    fake.write_text("ordinary text", encoding="utf-8")
    results["cli_invalid"] = invoke(
        [
            sys.executable,
            "-B",
            "egs/cli.py",
            "--base-url",
            base,
            "--format",
            "json",
            "ai",
            "attachment",
            "upload",
            "--file",
            str(fake),
        ]
    )
    assert results["cli_invalid"]["code"] != 0 and "校验失败" in results["cli_invalid"]["stdout"]
    results["cli_valid"] = invoke(
        [
            sys.executable,
            "-B",
            "egs/cli.py",
            "--base-url",
            base,
            "--format",
            "json",
            "ai",
            "attachment",
            "upload",
            "--file",
            str(images[0]),
        ]
    )
    assert results["cli_valid"]["code"] == 0
    env = dict(
        os.environ,
        ALL_IN_ONE_RUNTIME_MODE="strict",
        ALL_IN_ONE_DATA_DIR=str(output / "bad-runtime/data"),
        ALL_IN_ONE_DB_PATH=str(output / "bad-runtime/test.db"),
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    old_python = PROJECT_ROOT / ".venv-graph" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    results["rejected_launchers"] = []
    for args in (
        ["start.py", "--host", "127.0.0.1", "--port", str(port)],
        ["-m", "src.main"],
        ["egs/cli.py", "system", "serve", "--host", "127.0.0.1", "--port", str(port)],
    ):
        result = invoke(
            [str(old_python), "-B", *args], env={**env, "ALL_IN_ONE_HOST": "127.0.0.1", "ALL_IN_ONE_PORT": str(port)}
        )
        assert result["code"] != 0 and "环境不符合声明" in result["stderr"], result
        assert "启动成功" not in result["stdout"] + result["stderr"]
        with socket.socket() as check:
            assert check.connect_ex(("127.0.0.1", port)) != 0
        results["rejected_launchers"].append(result)
    results["modules"] = {}
    for module in ("ai", "knowledge", "strategy"):
        durations = []
        for _ in range(3):
            started = perf_counter()
            response = requests.get(base + f"/app/{module}/config", timeout=90)
            response.raise_for_status()
            durations.append((perf_counter() - started) * 1000)
        config = response.json()
        results["modules"][module] = {
            "components": len(config["components"]),
            "serialized_chars": len(json.dumps(config, ensure_ascii=False)),
            "ms": durations,
            "median_ms": median(durations),
        }
    (output / "verification.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Actual-process verification passed | timings={} modules={}", timings, results["modules"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.base_url, args.output)
