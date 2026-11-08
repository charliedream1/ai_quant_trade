"""Explicit Qlib subprocess selection, diagnostics and aligned signal comparison."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from threading import RLock
from typing import Any

import pandas as pd
import yaml
from dotenv import dotenv_values

from src.core.config import PROJECT_ROOT
from src.core.process_env import process_environment
from src.strategy.factors.research import forward_labels
from src.strategy.factors.statistics import information_ratio

_STATUS: dict[str, tuple[float, dict[str, Any]]] = {}
_LOCK = RLock()


def configuration() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/strategies/factor_monitor.yaml").read_text(encoding="utf-8"))


def interpreter(config: dict[str, Any] | None = None) -> Path:
    value = (
        os.environ.get("ALL_IN_ONE_QLIB_PYTHON")
        or dotenv_values(PROJECT_ROOT / ".env").get("ALL_IN_ONE_QLIB_PYTHON")
        or (config or configuration())["qlib_python"]
    )
    path = Path(value)
    path = path if path.is_absolute() else PROJECT_ROOT / path
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python") if path.is_dir() else path


def _invoke(payload: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any]:
    python = interpreter(config)
    if not python.is_file():
        raise ValueError("Qlib分析环境未配置，请配置项目内独立Python解释器")
    worker = PROJECT_ROOT / "src/engine/research/qlib_signal_worker.py"
    command = [str(python), "-B", str(worker)]
    if payload is None:
        command.append("--diagnose")
    result = subprocess.run(
        command,
        input=json.dumps(payload, allow_nan=False) if payload is not None else "",
        cwd=PROJECT_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=config["qlib_timeout_seconds"],
        check=False,
        env=process_environment("model"),
    )
    if result.returncode:
        raise ValueError(f"Qlib工作进程失败：{result.stderr.strip()}")
    return json.loads(result.stdout)


def signal_status(refresh: bool = False) -> dict[str, Any]:
    cfg = configuration()
    key = str(interpreter(cfg))
    with _LOCK:
        cached = _STATUS.get(key)
        if not refresh and cached and time.monotonic() - cached[0] < cfg["cache_seconds"]:
            return dict(cached[1])
        try:
            status = {
                **_invoke(None, cfg),
                "python": key,
                "next_step": "独立环境真实导入成功；模型Workflow仍需单独配置数据和执行入口",
            }
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            status = {"status": "missing", "version": "-", "python": key, "next_step": str(exc)}
        _STATUS[key] = time.monotonic(), status
        return dict(status)


def apply_qlib(
    panel: pd.DataFrame,
    history: dict[str, Any],
    as_of: str,
    reports: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    batches = []
    for report in reports:
        labels = forward_labels(history, report["params"]["horizon"], as_of)
        joined = panel.join(labels, how="inner")
        if joined.empty:
            raise ValueError("Qlib分析缺少已到期的有效标签")
        frame = joined.drop(columns="label_end").reset_index().astype(object)
        rows = frame.where(pd.notna(frame), None).to_dict("records")
        batches.append({"rows": rows, "factors": list(panel.columns)})
    result = _invoke({"batches": batches}, config)
    for report, batch in zip(reports, result["batches"], strict=True):
        _apply_result(report, batch)


def _apply_result(report: dict[str, Any], result: dict[str, Any]) -> None:
    for key, daily in report["history"].items():
        qlib = result["analysis"][key]
        for row in daily:
            values = qlib.get(row["date"], {})
            if values.get("ic") is None or values.get("rank_ic") is None:
                raise ValueError(f"Qlib未返回有效横截面：{row['date']} {key}")
            row.update(values)
        values = [row["rank_ic"] for row in daily]
        report["metrics"][key].update(
            {
                "ic_mean": sum(row["ic"] for row in daily) / len(daily) if daily else None,
                "rank_ic_mean": sum(values) / len(values) if values else None,
                "icir": information_ratio(values),
            }
        )
    report["backend"] = {
        "key": "qlib",
        "version": result["version"],
        "icir_convention": "RankIC均值/总体标准差，未年化",
    }
