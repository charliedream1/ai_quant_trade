"""Opt-in effect acceptance using the installed WorkBuddy free hy3 model."""

import json
import os
import re
from pathlib import Path
from time import perf_counter

import pytest
import requests
import yaml
from loguru import logger
from playwright.sync_api import expect, sync_playwright

from src.core.config import PROJECT_ROOT
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from tests.knowledge.workbuddy_hy3_runtime import Hy3Runtime, openai_bridge

pytestmark = pytest.mark.skipif(os.environ.get("KNOWLEDGE_HY3_LIVE") != "1", reason="Explicit real hy3 acceptance only")


def test_hy3_real_knowledge_effects(client, cli_command, tmp_path, monkeypatch):
    policy = yaml.safe_load(Path(__file__).with_name("hy3_acceptance.yaml").read_text(encoding="utf-8"))
    output = Path(os.environ["KNOWLEDGE_HY3_OUTPUT"]).resolve()
    assert output.is_relative_to(PROJECT_ROOT)
    output.mkdir(parents=True, exist_ok=True)
    runtime = Hy3Runtime(policy, output)
    monkeypatch.setenv("ALL_IN_ONE_DATA_MODE", "real")
    results = {}
    with openai_bridge(runtime) as endpoint:
        model = Repository().insert(
            "llm_models",
            {
                "name": "WorkBuddy CLI · Hy3 实测",
                "level": "fast",
                "purpose": "问答",
                "model_name": "hy3",
                "base_url": endpoint,
                "api_key": "",
                "is_default": 1,
                "enabled": 1,
                "timeout_seconds": 180,
                "max_tokens": 3000,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            },
        )
        documents = []
        for source in policy["documents"]:
            path = tmp_path / source["filename"]
            path.write_text(source["content"], encoding="utf-8")
            documents.append(path)
        isolated = policy["isolated_document"]
        response = client.post(
            "/api/v1/kb/documents",
            data={"library_name": policy["libraries"]["isolated"]},
            files={"file": (isolated["filename"], isolated["content"].encode())},
        ).json()
        assert response["code"] == 0, response
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1600, "height": 1100})
                page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
                page.goto(cli_command.base_url + "/app/?module=knowledge&view=library", wait_until="domcontentloaded")
                frame = page.frame_locator("iframe.workspace-frame.active")
                library = frame.locator("#kb-ingest-library input")
                expect(library).to_be_visible(timeout=90000)
                library.fill(policy["libraries"]["primary"])
                library.press("Enter")
                frame.get_by_role("button", name="创建知识库", exact=True).click()
                expect(frame.locator("#kb-ingest-status")).to_contain_text("已创建", timeout=30000)
                frame.locator("#kb-ingest-files input[type=file]").set_input_files([str(path) for path in documents])
                frame.get_by_role("button", name="文件入库", exact=True).click()
                expect(frame.locator("#kb-ingest-status")).to_contain_text(
                    policy["documents"][-1]["filename"], timeout=30000
                )
                assert "失败" not in frame.locator("#kb-ingest-status").inner_text()
                if page.locator("#notification-toasts .notification-card-top button").count():
                    page.locator("#notification-toasts .notification-card-top button").first.click()
                page.screenshot(path=str(output / "01-ingestion.png"))
                page.locator('[data-workspace-view-module="knowledge"][data-workspace-view="qa"]').click()
                frame.get_by_role("button", name="刷新库名", exact=True).click()
                frame.locator("#rag-library input").click()
                frame.get_by_role("option", name=policy["libraries"]["primary"], exact=True).click()
                started = perf_counter()
                frame.get_by_label("问题", exact=True).fill(policy["questions"]["synthesis"])
                frame.get_by_role("button", name="提问", exact=True).click()
                expect(frame.locator("#rag-chat-references")).to_contain_text("霁蓝回执", timeout=300000)
                expect(frame.locator("#rag-chat-history")).to_contain_text("QL-2026-1102", timeout=300000)
                history = Repository().db.query_one("SELECT * FROM kb_qa_history ORDER BY id DESC LIMIT 1")
                results["synthesis"] = {
                    "answer": history["answer"],
                    "references": json.loads(history["cited_docs"]),
                    "duration_seconds": round(perf_counter() - started, 2),
                    "session_id": history["session_id"],
                }
                for fact in policy["expectations"]["synthesis"]:
                    assert fact in history["answer"], (fact, history["answer"])
                assert len(re.findall(r"\[\d+\]", history["answer"])) >= 2
                page.screenshot(path=str(output / "02-answer.png"))
                frame.locator("#rag-chat-references").get_by_text("霁蓝回执", exact=True).filter(
                    visible=True
                ).first.click()
                panel = frame.locator(".file-reader-panel-left")
                expect(panel).to_be_visible(timeout=30000)
                assert (
                    abs(
                        panel.bounding_box()["width"]
                        / page.locator("iframe.workspace-frame.active").bounding_box()["width"]
                        - 0.5
                    )
                    < 0.02
                )
                preview = panel.frame_locator("iframe")
                expect(preview.locator("#markdown-preview")).to_contain_text("林岚和周衡", timeout=30000)
                page.screenshot(path=str(output / "03-citation.png"))
                panel.get_by_role("button", name="关闭文件阅读").click()
                attachment = tmp_path / policy["attachment"]["filename"]
                attachment.write_text(policy["attachment"]["content"], encoding="utf-8")
                frame.locator("#rag-attachments input[type=file]").set_input_files(str(attachment))
                frame.get_by_label("问题", exact=True).fill(policy["questions"]["attachment"])
                frame.get_by_role("button", name="提问", exact=True).click()
                expect(frame.locator("#rag-chat-history")).to_contain_text("HY3-ATT-6821", timeout=300000)
                latest = Repository().db.query_one("SELECT * FROM kb_qa_history ORDER BY id DESC LIMIT 1")
                results["attachment"] = {"answer": latest["answer"], "references": json.loads(latest["cited_docs"])}
                assert "许澄" in latest["answer"]
                assert any(
                    row["title"] == Path(policy["attachment"]["filename"]).stem
                    for row in results["attachment"]["references"]
                )
                page.screenshot(path=str(output / "04-attachment.png"))
                browser.close()
            for name in ("follow_up", "insufficient", "isolation"):
                started = perf_counter()
                response = requests.post(
                    cli_command.base_url + "/api/v1/kb/qa",
                    json={
                        "question": policy["questions"][name],
                        "library_name": policy["libraries"]["primary"],
                        "model_id": model["id"],
                        "retrieval_rounds": 4,
                        "session_id": history["session_id"] if name == "follow_up" else name,
                    },
                    timeout=600,
                ).json()
                assert response["code"] == 0, response
                results[name] = {**response["data"], "duration_seconds": round(perf_counter() - started, 2)}
                assert response["data"]["status"] in {"answered", "no_hits"}, response
                if name == "follow_up":
                    assert all(term in response["data"]["answer"] for term in policy["expectations"][name])
                if name == "isolation":
                    assert policy["expectations"]["forbidden_isolation_text"] not in response["data"]["answer"]
                    assert not response["data"]["references"]
                logger.info("Real hy3 case complete | case={} status={}", name, response["data"]["status"])
        finally:
            (output / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            (output / "model-summary.json").write_text(
                json.dumps(
                    {
                        "model": "hy3",
                        "catalog_credits": "x0.00",
                        "calls": len(runtime.records),
                        "native_tool_calls": 0,
                        "mocked_model": False,
                        "bridge": "local OpenAI-compatible HTTP to installed WorkBuddy CLI",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
