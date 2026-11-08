"""Local/remote entry points, persistent failure inspection and export ownership."""

import json
import os
import subprocess
import sys
from threading import Event
from time import monotonic

import pytest

import src.agent.skill_runner.export as export_module
from src.agent.skill_runner.catalog import preview, settings
from src.agent.skill_runner.export import export_skills
from src.agent.skill_runner.service import LocalSkillService
from src.core.config import PROJECT_ROOT


def invoke(*args):
    result = subprocess.run(
        [sys.executable, "-B", "egs/entrypoints/skills.py", *args],
        capture_output=True,
        encoding="utf-8",
        timeout=40,
        cwd=PROJECT_ROOT,
    )
    return result, json.loads(result.stdout.splitlines()[-1])


def test_ten_examples_preview_and_no_server_catalog(client):
    result, value = invoke("catalog")
    assert result.returncode == 0 and len(value["workflows"]) == 10
    assert value["web_required"] is False
    for name in settings()["workflows"]:
        result, value = invoke("preview", "--config", f"egs/examples/skills_examples/{name}.yaml")
        assert result.returncode == 0, result.stderr
        assert value["model_called"] is False and value["skill"] == name


def test_failed_run_is_inspectable_and_not_reported_as_cancelled(client):
    service = LocalSkillService()
    result = service.run(
        {"skill": "quant-backtest-review", "request": {"backtest_id": 9999999, "objective": "missing"}}
    )
    assert result["status"] == "failed" and result["error"]
    assert service.store.events(result["run_id"])[-1]["kind"] == "finished"
    assert {row["name"] for row in service.store.files(result["run_id"])} >= {"report.html", "result.json"}
    process, shown = invoke("show", result["run_id"])
    assert process.returncode == 1 and shown["run_id"] == result["run_id"]
    with pytest.raises(ValueError, match="重复"):
        service.execute(result["run_id"])


def test_recursion_unknown_config_and_outside_import_are_rejected(client, monkeypatch):
    with pytest.raises(ValueError):
        preview({"skill": "quant-alpha-mining", "request": {"name": "missing"}})
    with pytest.raises(ValueError):
        preview({"skill": "quant-market-review", "arbitrary": True})
    with pytest.raises(ValueError):
        preview({"skill": "quant-market-review", "request": {"kind": "single_stock_analysis"}})
    monkeypatch.setenv("ALL_IN_ONE_PROVIDER_DEPTH", "1")
    with pytest.raises(ValueError, match="不得再次"):
        LocalSkillService().register({"skill": "quant-market-review"})


def test_export_is_idempotent_and_preserves_modified_skill(client, tmp_path, monkeypatch):
    for name in settings()["workflows"]:
        source = tmp_path / "src/skills" / name / "SKILL.md"
        source.parent.mkdir(parents=True)
        source.write_bytes((PROJECT_ROOT / "src/skills" / name / "SKILL.md").read_bytes())
    monkeypatch.setattr(export_module, "PROJECT_ROOT", tmp_path)
    first = export_skills("codex")
    assert first == export_skills("codex") and first["skills"] == 10
    target = tmp_path / ".agents/skills/quant-market-review/SKILL.md"
    target.write_text("user-owned modification", encoding="utf-8")
    with pytest.raises(ValueError, match="同名内容"):
        export_skills("codex")
    assert target.read_text(encoding="utf-8") == "user-owned modification"
    with pytest.raises(ValueError, match="尚未核验"):
        export_skills("trae")


def test_api_catalog_preview_failure_artifacts_and_origin(client):
    catalog = client.get("/api/v1/research-skills").json()["data"]
    assert len(catalog["workflows"]) == 10
    providers = client.get("/api/v1/agent-providers").json()["data"]["providers"]
    assert {row["backend"] for row in providers} == {"api", "codex", "qoder", "trae", "codebuddy"}
    payload = {"skill": "quant-backtest-review", "request": {"backtest_id": 9999999, "objective": "missing"}}
    assert client.post("/api/v1/research-skills/preview", json=payload).json()["data"]["model_called"] is False
    run_id = client.post("/api/v1/research-skills/runs", json=payload).json()["data"]["run_id"]
    deadline = monotonic() + 10
    while True:
        row = client.get(f"/api/v1/research-skills/runs/{run_id}").json()["data"]
        if row["status"] not in {"registered", "running"}:
            break
        assert monotonic() < deadline
        Event().wait(0.02)
    assert row["status"] == "failed"
    assert client.get(f"/api/v1/research-skills/runs/{run_id}/files/report.html").status_code == 200
    assert (
        client.post(
            "/api/v1/research-skills/runs", json=payload, headers={"Origin": "https://untrusted.invalid"}
        ).json()["code"]
        != 0
    )


def test_remote_mode_uses_existing_client(cli_command):
    result, value = invoke("catalog", "--base-url", cli_command.base_url)
    assert result.returncode == 0 and len(value["workflows"]) == 10
    result = cli_command("provider", "list")
    assert len(result["data"]["providers"]) == 5


def test_local_composition_runs_actual_cost_ledger(client):
    result = LocalSkillService().run(
        {
            "skill": "quant-strategy-composition",
            "request": {
                "template": "rule_trend",
                "mode": "backtest",
                "agent_mode": "off",
                "symbols": ["600519", "300750"],
                "start_date": "2026-01-05",
                "end_date": "2026-05-29",
                "market": "CN",
            },
        }
    )
    assert result["status"] in {"finished", "completed", "partial"}, result
    assert result["result"]["result"]["metrics"]["execution_costs"]["sha256"]


def test_abandoned_foreground_run_is_interrupted_without_retry(client):
    service = LocalSkillService()
    row = service.register({"skill": "quant-market-review"})
    row["status"] = "running"
    service.store.save(row)
    service.store.heartbeat(row["run_id"])
    heartbeat = service.store.directory(row["run_id"]) / "heartbeat"
    os.utime(heartbeat, (1, 1))
    result = service.store.get(row["run_id"])
    assert result["status"] == "interrupted" and "进程已结束" in result["error"]
