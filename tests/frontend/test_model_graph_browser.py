"""The model mode preserves rule querying and reopens the same saved evidence graph."""

import json
import os
from pathlib import Path
from threading import Event
from time import sleep

import yaml
from playwright.sync_api import expect, sync_playwright

from src.engine.market.model_graph.service import GraphResearchService
from tests.engine.test_model_relation_graph import start, wait


def test_model_graph_switch_history_preview_and_export(client, cli_command, monkeypatch, tmp_path):
    values = yaml.safe_load(Path("tests/engine/model_graph_fixtures.yaml").read_text(encoding="utf-8"))
    actual = os.environ.get("MODEL_GRAPH_BROWSER_RESULTS")
    if actual:
        service = GraphResearchService()
        records = json.loads(Path(actual).read_text(encoding="utf-8"))
        for record in records:
            assert record["run"]["status"] == "completed"
            service.store.save(record["run"])
            (service.store.directory(record["run"]["run_id"]) / "graph.json").write_text(
                json.dumps(record["graph"], ensure_ascii=False), encoding="utf-8"
            )
    else:
        service, run = start(client, monkeypatch, values)
        assert wait(service, run["run_id"])["status"] == "completed"
        records = [{"run": service.detail(run["run_id"]), "graph": service.store.result(run["run_id"])}]
    output = Path(os.environ.get("MODEL_GRAPH_BROWSER_OUTPUT", str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=market&view=relations", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            mode = frame.locator("#relation-graph-mode")
            expect(mode).to_be_visible(timeout=90000)
            mode.locator('label:has(input[value="model"])').click()
            expect(frame.locator("#model-graph-generate")).to_be_visible()
            for record in records:
                run = record["run"]
                original = (service.store.directory(run["run_id"]) / "graph.json").read_bytes()
                frame.locator("#model-graph-run-id").locator("input,textarea").first.fill(run["run_id"])
                frame.locator("#model-graph-open").click()
                expected = record["graph"]["edges"][0]["description"]
                evidence = frame.locator("#model-graph-evidence")
                expect(evidence).to_contain_text(expected, timeout=30000)
                evidence.locator("summary").first.click()
                evidence.get_by_text("Frozen original context", exact=True).first.click()
                expect(evidence.locator("pre").first).to_be_visible()
                expect(frame.locator("#model-graph-plot .js-plotly-plot")).to_be_visible(timeout=30000)
                frame.locator("#model-graph-plot").scroll_into_view_if_needed()
                page.screenshot(path=str(output / (run["request"]["market"] + "-model-graph.png")))
                frame.locator("#model-graph-export").click()
                link = frame.locator("a[href*='graph.json']").first
                expect(link).to_be_visible(timeout=30000)
                with page.expect_download() as pending:
                    link.click()
                saved = output / (run["run_id"] + "-download.json")
                pending.value.save_as(str(saved))
                assert saved.read_bytes() == original
                assert (service.store.directory(run["run_id"]) / "graph.json").read_bytes() == original
            page.locator("#app-language-toggle").click()
            expect(evidence).to_contain_text(expected)
            page.locator("#app-language-toggle").click()
            expect(evidence).to_contain_text(expected)
            page.set_viewport_size({"width": 420, "height": 900})
            frame.locator("#model-graph-plot").scroll_into_view_if_needed()
            expect(frame.locator("#model-graph-plot .js-plotly-plot")).to_be_visible()
            page.screenshot(path=str(output / "model-graph-mobile.png"))
            mode.locator('label:has(input[value="rules"])').click()
            expect(frame.get_by_role("button", name="查询关系", exact=True)).to_be_visible()
        except Exception:
            page.screenshot(path=str(output / "failure.png"))
            (output / "failure-frame.txt").write_text(frame.locator("body").inner_text(), encoding="utf-8")
            raise
        finally:
            browser.close()


def test_browser_starts_and_cancels_research(client, cli_command, monkeypatch):
    from tests.engine.test_model_relation_graph import FixtureGeneration

    values = yaml.safe_load(Path("tests/engine/model_graph_fixtures.yaml").read_text(encoding="utf-8"))
    service, first = start(client, monkeypatch, values)
    assert wait(service, first["run_id"])["status"] == "completed"
    entered = Event()

    def blocking_complete(self, prompt):
        entered.set()
        while not self.cancelled():
            sleep(0.02)
        raise InterruptedError("Explicit browser cancellation fixture")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=market&view=relations", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            mode = frame.locator("#relation-graph-mode")
            expect(mode).to_be_visible(timeout=90000)
            mode.locator('label:has(input[value="model"])').click()
            frame.get_by_label("Target stock", exact=True).fill(values["target"])
            frame.get_by_text("Authorized knowledge evidence", exact=True).click()
            frame.get_by_label("Knowledge library (optional)", exact=True).fill(values["library"])
            frame.get_by_label("Selected document IDs (comma separated, optional)", exact=True).fill(
                str(first["request"]["document_ids"][0])
            )
            frame.locator("#model-graph-generate").click()
            key = frame.locator("#model-graph-run-id").locator("textarea,input").first
            expect(key).not_to_have_value("", timeout=30000)
            completed = key.input_value()
            assert wait(service, completed)["status"] == "completed"
            assert len(service.store.result(completed)["calls"]) == 2
            monkeypatch.setattr(FixtureGeneration, "complete", blocking_complete)
            frame.locator("#model-graph-generate").click()
            expect(key).not_to_have_value(completed, timeout=30000)
            pending = key.input_value()
            assert entered.wait(5)
            frame.locator("#model-graph-cancel").click()
            assert wait(service, pending)["status"] == "cancelled"
            expect(frame.locator("#model-graph-status")).to_contain_text("cancelled", timeout=10000)
        finally:
            browser.close()
