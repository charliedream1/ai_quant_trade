"""Page/evidence isolation and actual shared report-pipeline acceptance."""

import json
from threading import Event
from time import monotonic, sleep

import pytest

from src.core.page_analysis_snapshot import analysis_config, capture, evidence
from src.core.page_work import PageWork, activate, context, deactivate
from src.engine.insights import page_analysis
from src.engine.insights.store import InsightStore
from src.frontend.service_dispatch import callback_registry


def observed(kind="fundamentals", symbol="600519", region="all", topic="all"):
    return [{"measured": 12, "data_source": "Declared test observation"}]


@pytest.mark.parametrize("task", list(analysis_config()["presets"]))
def test_all_presets_accept_only_scoped_registered_observations(client, task):
    preset = analysis_config()["presets"][task]
    assert all(name in callback_registry() for name in preset["reads"])
    page = PageWork("1" * 32, 1)
    name = preset["reads"][0]
    arguments = {"kind": preset.get("match", {}).get("kind", "fundamentals")}
    value = observed()
    if name == "factor_job":
        value = {"status": "completed", "result": value}
    if name == "rag_chat":
        value = ("", [], value, "", None)
    with context(page):
        with pytest.raises(ValueError):
            evidence(preset, {})
        capture(name, observed, (), arguments, value)
        result = evidence(preset, {})
        assert result[0]["is_mock"] is True
        assert result[0]["data"]["observations"]
        with context(PageWork("2" * 32, 1)):
            with pytest.raises(ValueError):
                evidence(preset, {})
    with context(PageWork("1" * 32, 2)):
        with pytest.raises(ValueError):
            evidence(preset, {})


def test_changed_symbol_cannot_reuse_old_page_data(client):
    with context(PageWork("3" * 32, 1)):
        capture("stock", observed, (), {}, observed())
        with pytest.raises(ValueError, match="changed"):
            evidence(analysis_config()["presets"]["technical"], {"symbol": "00700.HK"})


def test_market_switch_cannot_relabel_old_observations(client):
    from src.data.manager import REQUEST_MARKET

    with context(PageWork("6" * 32, 1)):
        token = REQUEST_MARKET.set("CN")
        capture("stock", observed, (), {}, observed())
        REQUEST_MARKET.set("HK")
        try:
            with pytest.raises(ValueError):
                evidence(analysis_config()["presets"]["technical"], {})
        finally:
            REQUEST_MARKET.reset(token)


def test_current_commentary_does_not_relax_experiment_admission(monkeypatch):
    from src.engine.insights import page_generation

    calls = []
    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "1")
    monkeypatch.setattr(page_generation, "require_native", lambda selection, **kwargs: calls.append(kwargs) or {})
    page_generation.capability("technical", {"backend": "codex"})
    page_generation.capability("backtest", {"backend": "codex"})
    assert calls == [{"strict": False}, {}]
    assert not page_generation.current_commentary("backtest", "codex")


def test_demo_data_does_not_silently_start_real_cli(client, monkeypatch):
    from src.engine.insights import page_generation

    monkeypatch.delenv("ALL_IN_ONE_ENABLE_REAL_CLI", raising=False)
    with pytest.raises(ValueError):
        page_generation.capability("technical", {"backend": "codex"})


def wait_finished(identifier):
    started = monotonic()
    while monotonic() - started < 15:
        result = InsightStore().detail(identifier)
        if result["status"] != "running":
            return result
        sleep(0.05)
    raise AssertionError("Report did not reach a terminal state")


def test_pipeline_reads_actual_skill_and_renders_escaped_identical_html(client, monkeypatch):
    from src.engine.insights import execution

    seen = []
    monkeypatch.setattr(execution, "validate_backend", lambda payload, cfg: {"model_name": "declared model"})

    def generate(prompt, payload, cfg, emit):
        assert "Page evidence analysis" in prompt
        assert "method/SKILL" not in prompt
        assert "12" in prompt
        seen.append(payload["page_task"])
        return json.dumps(
            {
                "title": "Declared report",
                "summary": "Evidence-bound",
                "sections": [
                    {"heading": heading, "paragraphs": ["<img src=x onerror=alert(1)>"], "source_ids": ["E1"]}
                    for heading in cfg["tasks"]["page_analysis"]["sections"]
                ],
                "risks": [],
                "missing": [],
            }
        )

    monkeypatch.setattr(execution, "generate_text", generate)
    with context(PageWork("4" * 32, 1)):
        capture("stock", observed, (), {}, observed())
        row = page_analysis.start("technical", {"backend": "api"}, {"symbol": "600519"})
        completed = wait_finished(row["run_id"])
    assert completed["status"] == "partial", completed
    assert seen == ["technical"]
    html = InsightStore().artifact(row["run_id"], "report.html").read_text(encoding="utf-8")
    assert "&lt;img" in html and "<img src=x" not in html
    assert "E1" in html
    assert "method/single_stock_analysis/SKILL.md" in completed["skills"]


def test_page_leave_cancels_owned_analysis(client, monkeypatch):
    from src.engine.insights import execution

    entered = Event()
    monkeypatch.setattr(execution, "validate_backend", lambda *args: {})

    def generate(prompt, payload, cfg, emit):
        entered.set()
        while not payload["_cancelled"]():
            sleep(0.02)
        raise InterruptedError("Declared source cancelled")

    monkeypatch.setattr(execution, "generate_text", generate)
    page = activate("5" * 32, 1)
    with context(page):
        capture("stock", observed, (), {}, observed())
        row = page_analysis.start("technical", {"backend": "api"}, {})
    assert entered.wait(5)
    with context(page):
        with pytest.raises(ValueError, match="already"):
            page_analysis.start("technical", {"backend": "api"}, {})
    deactivate(page.owner, page.revision)
    assert wait_finished(row["run_id"])["status"] in {"failed", "cancelled"}


def test_actual_cli_process_receives_skill_and_returns_html(client, monkeypatch):
    import sys

    from src.engine.insights import page_generation
    from src.strategy.codex_cli import CodexCliRunner

    class DeclaredRunner(CodexCliRunner):
        def command(self, prompt, **kwargs):
            from src.core.config import PROJECT_ROOT

            return [
                sys.executable,
                "-c",
                f"import sys,runpy; sys.path.insert(0,{str(PROJECT_ROOT)!r}); runpy.run_module('tests.frontend.page_cli_fixture',run_name='__main__')",
            ]

    monkeypatch.setattr(page_generation, "CodexCliRunner", DeclaredRunner)
    monkeypatch.setenv("ALL_IN_ONE_ENABLE_REAL_CLI", "1")
    monkeypatch.setattr(page_generation, "require_native", lambda *args, **kwargs: {"backend": "codex"})
    with context(PageWork("7" * 32, 1)):
        capture("stock", observed, (), {}, observed())
        row = page_analysis.start("technical", {"backend": "codex", "model_name": "declared-protocol"}, {})
        result = wait_finished(row["run_id"])
    assert result["status"] == "partial", result
    html = InsightStore().artifact(row["run_id"], "report.html").read_text(encoding="utf-8")
    assert "Declared native CLI report" in html and "E1" in html
