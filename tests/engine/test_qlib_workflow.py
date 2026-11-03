"""Qlib workflow run registry regression tests."""

from __future__ import annotations

import subprocess


def test_qlib_workflow_registers_auditable_run(client):
    from src.engine.research import QlibWorkflowService

    service = QlibWorkflowService()
    status = service.status()

    assert status["config"]["workflow_path"]
    assert status["diagnostic"]["key"] == "qlib"

    run = service.create_run({"run_type": "workflow", "params": {"experiment_name": "engine_qlib"}})

    assert run["run_id"] > 0
    assert run["run_type"] == "workflow"
    assert run["experiment_name"] == "engine_qlib"
    assert run["status"] in {"blocked", "running", "finished", "failed"}
    if run["status"] == "blocked":
        assert run["metrics"]["registered_only"] is True

    runs = service.list_runs(run_type="workflow")
    assert runs["total"] == 1
    assert runs["items"][0]["run_id"] == run["run_id"]


def test_qlib_workflow_executes_qrun_when_ready(client, tmp_path, monkeypatch):
    from src.engine.research import qlib_workflow

    provider = tmp_path / "qlib_data"
    provider.mkdir()
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text("qlib_init:\n  provider_uri: ${QLIB_PROVIDER_URI}\n", encoding="utf-8")
    config = tmp_path / "qlib.yaml"
    config.write_text(
        "\n".join(
            [
                f'provider_uri: "{provider.as_posix()}"',
                f'workflow_path: "{workflow.as_posix()}"',
                'experiment_name: "unit_qlib"',
                'market: "csi300"',
                'benchmark: "SH000300"',
                'region: "cn"',
            ]
        ),
        encoding="utf-8",
    )

    class FakeDiagnostic:
        def to_dict(self) -> dict[str, str]:
            return {
                "key": "qlib",
                "label": "Qlib 投研引擎",
                "status": "available",
                "version": "test",
                "license": "MIT",
                "description": "fake qlib",
                "next_step": "",
            }

    captured: dict[str, object] = {}
    artifact_dir = tmp_path / "qlib_artifacts"

    def fake_run(args, **kwargs):
        kwargs["args"] = args
        captured.update(kwargs)
        artifact_dir.mkdir()
        (artifact_dir / "train_metrics.json").write_text(
            '{"train_loss": 0.12, "valid_loss": 0.18, "rank_ic": 0.043}',
            encoding="utf-8",
        )
        (artifact_dir / "portfolio_metrics.csv").write_text(
            "annualized_return,max_drawdown,sharpe,information_ratio\n0.21,-0.08,1.25,0.74\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(args, 0, stdout="workflow ok", stderr="")

    monkeypatch.setattr(qlib_workflow, "qlib_diagnostic", lambda: FakeDiagnostic())
    monkeypatch.setattr(qlib_workflow.shutil, "which", lambda name: "qrun" if name == "qrun" else None)
    monkeypatch.setattr(qlib_workflow.subprocess, "run", fake_run)

    service = qlib_workflow.QlibWorkflowService(config_path=config)
    status = service.status()
    run = service.create_run(
        {
            "run_type": "workflow",
            "params": {"experiment_name": "ready_qlib", "artifact_dir": artifact_dir.as_posix()},
        }
    )

    assert status["ready"] is True
    assert run["status"] == "finished"
    assert run["metrics"]["registered_only"] is False
    assert run["metrics"]["returncode"] == 0
    assert run["metrics"]["stdout_tail"] == "workflow ok"
    assert run["metrics"]["training_metrics"]["rank_ic"] == 0.043
    assert run["metrics"]["portfolio_metrics"]["sharpe"] == 1.25
    assert run["artifact_count"] >= 2
    assert any(item["path"].endswith("portfolio_metrics.csv") for item in run["artifacts"])
    assert captured["args"] == ["qrun", str(workflow)]
    assert captured["cwd"] == str(qlib_workflow.PROJECT_ROOT)
    assert captured["env"]["QLIB_PROVIDER_URI"] == provider.as_posix()
    assert captured["env"]["QLIB_EXPERIMENT_NAME"] == "ready_qlib"
