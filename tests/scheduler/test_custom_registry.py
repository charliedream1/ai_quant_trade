from __future__ import annotations

from pathlib import Path

import src.core.config as config_module
from src.core.config import PROJECT_ROOT
from src.scheduler.jobs import execute_scheduled_job


def test_custom_executor_registry_loads_configured_handler(tmp_path, monkeypatch):
    config_path = _write_executor_config(tmp_path, PROJECT_ROOT)
    monkeypatch.setenv("ALL_IN_ONE_SCHEDULER_EXECUTORS_PATH", str(config_path))
    config_module._SETTINGS = None

    result = execute_scheduled_job(
        {
            "job_id": 100,
            "name": "自定义样例",
            "job_type": "custom",
            "target": {"executor_key": "echo", "message": "hello-registry"},
        }
    )

    assert result["status"] == "成功"
    assert "hello-registry" in result["summary"]
    assert result["details"]["executor_key"] == "echo"


def test_unknown_custom_executor_is_skipped(monkeypatch):
    monkeypatch.delenv("ALL_IN_ONE_SCHEDULER_EXECUTORS_PATH", raising=False)
    config_module._SETTINGS = None

    result = execute_scheduled_job({"job_type": "custom", "target": {"executor_key": "missing"}})

    assert result["status"] == "跳过"
    assert "未注册" in result["summary"]


def test_custom_scheduler_job_via_api(client, tmp_path, monkeypatch):
    config_path = _write_executor_config(tmp_path, PROJECT_ROOT)
    monkeypatch.setenv("ALL_IN_ONE_SCHEDULER_EXECUTORS_PATH", str(config_path))
    config_module._SETTINGS = None

    job = client.post(
        "/api/v1/jobs",
        json={
            "name": "自定义执行体",
            "job_type": "custom",
            "cron": "*/10 * * * *",
            "target": {"executor_key": "echo", "message": "hello-api"},
        },
    ).json()
    assert job["code"] == 0

    result = client.post(f"/api/v1/jobs/{job['data']['job_id']}/trigger").json()

    assert result["code"] == 0
    assert result["data"]["status"] == "成功"
    assert "hello-api" in result["data"]["result_summary"]


def test_process_timeout_terminates_custom_executor(client, tmp_path, monkeypatch):
    config_path = _write_executor_config(tmp_path, PROJECT_ROOT)
    marker_path = tmp_path / "sleep-done.txt"
    monkeypatch.setenv("ALL_IN_ONE_SCHEDULER_EXECUTORS_PATH", str(config_path))
    config_module._SETTINGS = None

    job = client.post(
        "/api/v1/jobs",
        json={
            "name": "进程超时",
            "job_type": "custom",
            "cron": "*/10 * * * *",
            "target": {
                "executor_key": "sleep",
                "sleep_seconds": 3,
                "marker_path": str(marker_path),
                "timeout_seconds": 0.2,
                "timeout_mode": "process",
            },
        },
    ).json()
    assert job["code"] == 0

    result = client.post(f"/api/v1/jobs/{job['data']['job_id']}/trigger").json()

    assert result["code"] == 0
    assert result["data"]["status"] == "超时"
    assert "超过 0.2 秒" in result["data"]["result_summary"]
    assert not marker_path.exists()


def _write_executor_config(tmp_path: Path, project_root: Path) -> Path:
    handler_path = project_root / "egs" / "scheduler_custom_handlers.py"
    config_path = tmp_path / "scheduler_executors.yaml"
    config_path.write_text(
        "\n".join(
            [
                "executors:",
                "  echo:",
                f"    path: {handler_path.as_posix()}",
                "    callable: echo_task",
                "    description: test executor",
                "  sleep:",
                f"    path: {handler_path.as_posix()}",
                "    callable: sleep_task",
                "    description: process timeout test executor",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path
