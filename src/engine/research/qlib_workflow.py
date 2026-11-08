"""Qlib workflow configuration and run registry service."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from src.core.logger import get_logger
from src.core.process_env import process_environment
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.engine.backtest.engines import qlib_diagnostic

PROJECT_ROOT = Path(__file__).resolve().parents[3]
USER_CONFIG_PATH = PROJECT_ROOT / "egs/config/models/qlib.yaml"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "egs" / "config" / "models" / "qlib.example.yaml"

DEFAULT_RUN_TYPE = "workflow"
RUN_TYPES = {"workflow", "backtest", "factor"}
READY_STATUS = "planned"
RUNNING_STATUS = "running"
FINISHED_STATUS = "finished"
FAILED_STATUS = "failed"
BLOCKED_STATUS = "blocked"
DEFAULT_TIMEOUT_SECONDS = 1800
MAX_OUTPUT_CHARS = 8000
MAX_ARTIFACT_FILES = 30
MAX_ARTIFACT_SCAN_FILES = 300
MAX_METRIC_FILES = 12
ARTIFACT_PARAM_KEYS = (
    "artifact_dir",
    "artifacts_dir",
    "output_dir",
    "result_dir",
    "recorder_dir",
    "mlruns_dir",
)
TRAINING_METRIC_KEYS = {
    "loss",
    "train_loss",
    "valid_loss",
    "validation_loss",
    "rmse",
    "mae",
    "mse",
    "auc",
    "ic",
    "rank_ic",
    "information_coefficient",
}
PORTFOLIO_METRIC_KEYS = {
    "annualized_return",
    "annual_return",
    "return",
    "excess_return",
    "max_drawdown",
    "information_ratio",
    "sharpe",
    "sortino",
    "volatility",
    "benchmark_return",
    "turnover",
}
PATH_PATTERN = re.compile(r"(?P<path>(?:[A-Za-z]:[\\/]|/|\.{1,2}[\\/])[^\s'\"<>]+)")


class QlibWorkflowService:
    """Manage Qlib experiment configuration and auditable run records."""

    def __init__(self, repo: Repository | None = None, config_path: Path | None = None) -> None:
        self.repo = repo or Repository()
        self.config_path = config_path or (USER_CONFIG_PATH if USER_CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH)
        self.log = get_logger("qlib_workflow")

    def status(self) -> dict[str, Any]:
        config = self.config()
        diagnostic = qlib_diagnostic().to_dict()
        workflow_path = str(config.get("workflow_path") or "")
        provider_uri = str(config.get("provider_uri") or "")
        blocker = _execution_blocker(diagnostic, workflow_path, provider_uri, str(config.get("qrun_path") or ""))
        ready = not blocker
        return {
            "ready": ready,
            "status": READY_STATUS if ready else BLOCKED_STATUS,
            "config_path": str(self.config_path),
            "config": config,
            "diagnostic": diagnostic,
            "next_step": blocker or _next_step(diagnostic, workflow_path, provider_uri),
            "latest_runs": self.list_runs(page=1, page_size=10)["items"],
        }

    def config(self) -> dict[str, Any]:
        payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError("Qlib 配置必须是 YAML 对象")
        return payload

    def create_run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        config = self.config()
        diagnostic = qlib_diagnostic().to_dict()
        run_type = _normalize_run_type(payload.get("run_type"))
        workflow_path = str(payload.get("workflow_path") or config.get("workflow_path") or "").strip()
        provider_uri = str(payload.get("provider_uri") or config.get("provider_uri") or "").strip()
        params = _normalize_params(payload.get("params"))
        params.setdefault("experiment_name", config.get("experiment_name") or "all_in_one_qlib_research")
        params.setdefault("market", config.get("market") or "")
        params.setdefault("benchmark", config.get("benchmark") or "")
        params.setdefault("region", config.get("region") or "")
        for artifact_key in ARTIFACT_PARAM_KEYS:
            if config.get(artifact_key):
                params.setdefault(artifact_key, config.get(artifact_key))
        if config.get("qrun_path"):
            params.setdefault("qrun_path", config.get("qrun_path"))
        timeout_seconds = _normalize_timeout(payload.get("timeout_seconds"), config)
        blocker = _execution_blocker(diagnostic, workflow_path, provider_uri, str(config.get("qrun_path") or ""))
        status = BLOCKED_STATUS if blocker else RUNNING_STATUS
        now = utc_now_iso()
        run = self.repo.insert(
            "qlib_runs",
            {
                "run_type": run_type,
                "status": status,
                "workflow_path": workflow_path,
                "provider_uri": provider_uri,
                "params": params,
                "metrics": {
                    "qlib_status": diagnostic.get("status"),
                    "qlib_version": diagnostic.get("version"),
                    "registered_only": bool(blocker),
                    "runner": None if blocker else "qrun",
                    "timeout_seconds": timeout_seconds,
                },
                "artifacts": [
                    {
                        "artifact_type": "config",
                        "title": "Qlib workflow 配置",
                        "path": workflow_path,
                    }
                ],
                "error_msg": blocker,
                "created_at": now,
                "started_at": None if blocker else now,
                "finished_at": None,
            },
        )
        if not blocker:
            run = self._execute_registered_run(
                int(run["id"]),
                workflow_path=workflow_path,
                provider_uri=provider_uri,
                params=params,
                timeout_seconds=timeout_seconds,
                diagnostic=diagnostic,
            )
        self.log.info(
            "qlib workflow run handled | run_id={} run_type={} status={} workflow_path={}",
            run["id"],
            run_type,
            run["status"],
            workflow_path or "-",
        )
        return self._public_run(run)

    def _execute_registered_run(
        self,
        run_id: int,
        workflow_path: str,
        provider_uri: str,
        params: dict[str, Any],
        timeout_seconds: int,
        diagnostic: dict[str, str],
    ) -> dict[str, Any]:
        started = time.monotonic()
        qrun_path = str(params.get("qrun_path") or os.environ.get("ALL_IN_ONE_QLIB_QRUN") or "").strip()
        qrun_path = qrun_path or shutil.which("qrun") or ""
        if not qrun_path:
            return self._finish_run(
                run_id,
                status=BLOCKED_STATUS,
                diagnostic=diagnostic,
                error_msg="pyqlib 已可导入，但当前环境找不到 qrun 命令；请确认 pyqlib 命令行入口已安装并在 PATH 中。",
                registered_only=True,
                runner=None,
                timeout_seconds=timeout_seconds,
                execution={},
                params=params,
            )

        workflow_file = _resolve_project_path(workflow_path)
        command = [qrun_path, str(workflow_file)]
        env = process_environment("model")
        env["PYTHONIOENCODING"] = "utf-8"
        env["QLIB_PROVIDER_URI"] = provider_uri
        env["QLIB_EXPERIMENT_NAME"] = str(params.get("experiment_name") or "")
        self.log.info(
            "qlib qrun started | run_id={} command={} provider_uri={}",
            run_id,
            command,
            provider_uri,
        )
        try:
            completed = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            execution = {
                "command": command,
                "returncode": completed.returncode,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "stdout_tail": _tail_output(completed.stdout),
                "stderr_tail": _tail_output(completed.stderr),
            }
            if completed.returncode == 0:
                self.log.info("qlib qrun finished | run_id={} duration_ms={}", run_id, execution["duration_ms"])
                return self._finish_run(
                    run_id,
                    status=FINISHED_STATUS,
                    diagnostic=diagnostic,
                    error_msg="",
                    registered_only=False,
                    runner="qrun",
                    timeout_seconds=timeout_seconds,
                    execution=execution,
                    params=params,
                )
            self.log.warning(
                "qlib qrun failed | run_id={} returncode={} stderr={}",
                run_id,
                completed.returncode,
                execution["stderr_tail"],
            )
            return self._finish_run(
                run_id,
                status=FAILED_STATUS,
                diagnostic=diagnostic,
                error_msg=f"qrun 执行失败，返回码 {completed.returncode}。请查看 metrics.stderr_tail。",
                registered_only=False,
                runner="qrun",
                timeout_seconds=timeout_seconds,
                execution=execution,
                params=params,
            )
        except subprocess.TimeoutExpired as exc:
            execution = {
                "command": command,
                "returncode": None,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "stdout_tail": _tail_output(exc.stdout),
                "stderr_tail": _tail_output(exc.stderr),
            }
            self.log.warning("qlib qrun timeout | run_id={} timeout_seconds={}", run_id, timeout_seconds)
            return self._finish_run(
                run_id,
                status=FAILED_STATUS,
                diagnostic=diagnostic,
                error_msg=f"qrun 执行超时，超过 {timeout_seconds} 秒未完成。",
                registered_only=False,
                runner="qrun",
                timeout_seconds=timeout_seconds,
                execution=execution,
                params=params,
            )
        except OSError as exc:
            self.log.exception("qlib qrun os error | run_id={}", run_id)
            return self._finish_run(
                run_id,
                status=FAILED_STATUS,
                diagnostic=diagnostic,
                error_msg=f"qrun 启动失败：{exc}",
                registered_only=False,
                runner="qrun",
                timeout_seconds=timeout_seconds,
                execution={
                    "command": command,
                    "returncode": None,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "stdout_tail": "",
                    "stderr_tail": str(exc),
                },
                params=params,
            )

    def _finish_run(
        self,
        run_id: int,
        status: str,
        diagnostic: dict[str, str],
        error_msg: str,
        registered_only: bool,
        runner: str | None,
        timeout_seconds: int,
        execution: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        row = self.repo.get("qlib_runs", run_id)
        parsed = _parse_qlib_outputs(params, execution)
        metrics = {
            "qlib_status": diagnostic.get("status"),
            "qlib_version": diagnostic.get("version"),
            "registered_only": registered_only,
            "runner": runner,
            "timeout_seconds": timeout_seconds,
            **execution,
            "training_metrics": parsed["training_metrics"],
            "portfolio_metrics": parsed["portfolio_metrics"],
            "artifact_count": len(parsed["artifacts"]),
            "artifact_roots": parsed["roots"],
        }
        artifacts = [
            {
                "artifact_type": "config",
                "title": "Qlib workflow 配置",
                "path": row.get("workflow_path") or "",
            },
            {
                "artifact_type": "execution",
                "title": "Qlib qrun 执行输出",
                "path": "",
                "stdout_tail": execution.get("stdout_tail") or "",
                "stderr_tail": execution.get("stderr_tail") or "",
            },
        ] + parsed["artifacts"]
        return self.repo.update(
            "qlib_runs",
            run_id,
            {
                "status": status,
                "metrics": metrics,
                "artifacts": artifacts,
                "error_msg": error_msg,
                "finished_at": utc_now_iso(),
            },
        )

    def list_runs(
        self,
        run_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        where = ""
        params: list[Any] = []
        if run_type:
            where = "run_type = ?"
            params.append(_normalize_run_type(run_type))
        result = self.repo.page(
            "qlib_runs",
            page=page,
            page_size=page_size,
            where=where,
            params=params,
            order_by="created_at DESC",
        )
        result["items"] = [self._public_run(row) for row in result["items"]]
        return result

    def detail(self, run_id: int) -> dict[str, Any]:
        return self._public_run(self.repo.get("qlib_runs", run_id))

    @staticmethod
    def _public_run(row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        item["run_id"] = item.get("id")
        item["params"] = json_loads(item.get("params"), {})
        item["metrics"] = json_loads(item.get("metrics"), {})
        item["artifacts"] = json_loads(item.get("artifacts"), [])
        params = item.get("params") or {}
        metrics = item.get("metrics") or {}
        item["experiment_name"] = params.get("experiment_name") or ""
        item["market"] = params.get("market") or ""
        item["benchmark"] = params.get("benchmark") or ""
        item["training_metrics"] = metrics.get("training_metrics") or {}
        item["portfolio_metrics"] = metrics.get("portfolio_metrics") or {}
        item["artifact_count"] = metrics.get("artifact_count") or len(item.get("artifacts") or [])
        return item


def _normalize_run_type(value: Any) -> str:
    run_type = str(value or DEFAULT_RUN_TYPE).strip().lower()
    if run_type not in RUN_TYPES:
        raise ValueError(f"不支持的 Qlib 运行类型：{run_type}")
    return run_type


def _normalize_params(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Qlib 运行参数必须是 JSON 对象")


def _normalize_timeout(value: Any, config: dict[str, Any]) -> int:
    raw = value
    if raw in (None, ""):
        raw = config.get("timeout_seconds") or config.get("run_timeout_seconds") or DEFAULT_TIMEOUT_SECONDS
    timeout = int(raw)
    if timeout <= 0:
        raise ValueError("Qlib timeout_seconds 必须大于 0")
    return min(timeout, 24 * 60 * 60)


def _next_step(diagnostic: dict[str, str], workflow_path: str, provider_uri: str) -> str:
    if diagnostic.get("status") != "available":
        return diagnostic.get("next_step") or "请先安装 pyqlib 并配置数据目录。"
    if not provider_uri:
        return "请配置 Qlib provider_uri 数据目录。"
    if not workflow_path:
        return "请配置 Qlib workflow YAML 路径。"
    return "Qlib 环境与配置已就绪；点击创建运行会调用 qrun 执行 workflow，并在运行记录中回填状态和输出尾部。"


def _execution_blocker(diagnostic: dict[str, str], workflow_path: str, provider_uri: str, qrun_path: str = "") -> str:
    message = _next_step(diagnostic, workflow_path, provider_uri)
    if diagnostic.get("status") != "available" or not workflow_path or not provider_uri:
        return message
    workflow_file = _resolve_project_path(workflow_path)
    if not workflow_file.exists() or not workflow_file.is_file():
        return f"Qlib workflow 文件不存在：{workflow_file}"
    if workflow_file.suffix.lower() not in {".yaml", ".yml"}:
        return f"Qlib workflow 文件必须是 YAML：{workflow_file}"
    provider_path = _maybe_local_provider_path(provider_uri)
    if provider_path is not None and not provider_path.exists():
        return f"Qlib provider_uri 数据目录不存在：{provider_path}"
    if not (qrun_path or os.environ.get("ALL_IN_ONE_QLIB_QRUN") or shutil.which("qrun")):
        return "pyqlib 已可导入，但当前环境找不到 qrun 命令；请确认 pyqlib 命令行入口已安装并在 PATH 中。"
    return ""


def _resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _maybe_local_provider_path(value: str) -> Path | None:
    if not value or "://" in value:
        return None
    path = Path(value).expanduser()
    if path.is_absolute() or value.startswith((".", "~")) or "\\" in value or "/" in value:
        return path if path.is_absolute() else PROJECT_ROOT / path
    return None


def _parse_qlib_outputs(params: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
    roots = _artifact_roots(params, execution)
    artifact_rows: list[dict[str, Any]] = []
    training_metrics: dict[str, Any] = {}
    portfolio_metrics: dict[str, Any] = {}
    metric_files = 0
    for root in roots:
        for path in _artifact_files(root):
            artifact_rows.append(_artifact_row(path))
            if metric_files >= MAX_METRIC_FILES:
                continue
            metrics = _metrics_from_file(path)
            if not metrics:
                continue
            metric_files += 1
            _merge_metrics(training_metrics, metrics, TRAINING_METRIC_KEYS)
            _merge_metrics(portfolio_metrics, metrics, PORTFOLIO_METRIC_KEYS)
    output_metrics = _metrics_from_text(
        "\n".join(str(execution.get(key) or "") for key in ("stdout_tail", "stderr_tail"))
    )
    _merge_metrics(training_metrics, output_metrics, TRAINING_METRIC_KEYS)
    _merge_metrics(portfolio_metrics, output_metrics, PORTFOLIO_METRIC_KEYS)
    return {
        "roots": [str(path) for path in roots],
        "artifacts": artifact_rows[:MAX_ARTIFACT_FILES],
        "training_metrics": training_metrics,
        "portfolio_metrics": portfolio_metrics,
    }


def _artifact_roots(params: dict[str, Any], execution: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    for key in ARTIFACT_PARAM_KEYS:
        raw = params.get(key)
        if raw in (None, ""):
            continue
        candidates.append(_resolve_project_path(str(raw)))
    output_text = "\n".join(str(execution.get(key) or "") for key in ("stdout_tail", "stderr_tail"))
    for match in PATH_PATTERN.finditer(output_text):
        path = _resolve_project_path(match.group("path").rstrip(".,;:)]}"))
        if path.exists() and (PROJECT_ROOT in path.parents or path == PROJECT_ROOT):
            candidates.append(path)
    unique: list[Path] = []
    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.exists() and str(resolved) not in seen:
            unique.append(resolved)
            seen.add(str(resolved))
    return unique


def _artifact_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        files.append(path)
        if len(files) >= MAX_ARTIFACT_SCAN_FILES:
            break
    files.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)
    return files[:MAX_ARTIFACT_FILES]


def _artifact_row(path: Path) -> dict[str, Any]:
    return {
        "artifact_type": _artifact_type(path),
        "title": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".json", ".csv", ".xlsx", ".pkl"}:
        return "metric_or_result"
    if suffix in {".png", ".jpg", ".jpeg", ".html"}:
        return "report"
    if suffix in {".log", ".txt"}:
        return "log"
    return "artifact"


def _metrics_from_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            return _flatten_metrics(payload)
        if suffix == ".csv":
            return _metrics_from_csv(path)
        if suffix in {".txt", ".log"}:
            return _metrics_from_text(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return {}


def _metrics_from_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {}
    last = rows[-1]
    metrics: dict[str, Any] = {}
    for key, value in last.items():
        metric_value = _metric_value(value)
        if key and metric_value is not None:
            metrics[str(key).strip()] = metric_value
    return metrics


def _metrics_from_text(text: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" not in line and "=" not in line:
            continue
        for key in TRAINING_METRIC_KEYS | PORTFOLIO_METRIC_KEYS:
            pattern = rf"\b{re.escape(key)}\b\s*[:=]\s*(-?\d+(?:\.\d+)?)"
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                metrics[key] = _metric_value(match.group(1))
    return metrics


def _flatten_metrics(payload: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key, value in payload.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_metrics(value, name))
        return result
    if isinstance(payload, list):
        if payload and isinstance(payload[-1], dict):
            return _flatten_metrics(payload[-1], prefix)
        return {}
    value = _metric_value(payload)
    return {prefix: value} if prefix and value is not None else {}


def _merge_metrics(target: dict[str, Any], metrics: dict[str, Any], keys: set[str]) -> None:
    for key, value in metrics.items():
        normalized = str(key).lower().replace(" ", "_")
        leaf = normalized.rsplit(".", 1)[-1]
        if leaf in keys and leaf not in target:
            target[leaf] = value


def _metric_value(value: Any) -> float | int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not (number == number and abs(number) != float("inf")):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 6)


def _tail_output(value: Any) -> str:
    if value is None:
        return ""
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[-MAX_OUTPUT_CHARS:]
