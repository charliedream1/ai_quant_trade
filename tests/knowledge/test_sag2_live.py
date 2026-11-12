"""Opt-in actual Hy3 and cached BGE inference with inspectable acceptance artifacts."""

import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path
from statistics import median

import pytest
import requests
import yaml
from loguru import logger
from playwright.sync_api import expect, sync_playwright

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.files import KnowledgeFiles
from src.knowledge.sag2_retrieval import SAG2Retrieval
from tests.knowledge.workbuddy_hy3_runtime import Hy3Runtime, openai_bridge

pytestmark = pytest.mark.skipif(os.environ.get("SAG2_LIVE") != "1", reason="Requires explicit live-model acceptance")


def write_results(output, summary):
    (output / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def check_answer(result, expected, allowed, sources):
    answer = result["answer"]
    refs = result["references"]
    cited = [int(number) for number in re.findall(r"\[(\d+)\]", answer)]
    return {
        "answered": result["status"] == "answered",
        "facts": {fact: fact in answer for fact in expected},
        "valid_citation_numbers": bool(cited) and all(1 <= index <= len(refs) for index in cited),
        "permitted_documents": bool(refs) and all(row["doc_id"] in allowed for row in refs),
        # Markdown chunking normalizes blank lines; non-whitespace text must remain original.
        "original_passages": bool(refs)
        and all(
            re.sub(r"\s+", " ", row["snippet"]).strip() in re.sub(r"\s+", " ", sources[row["doc_id"]]).strip()
            for row in refs
        ),
        "fact_support": all(any(fact in row["snippet"] for row in refs) for fact in expected),
    }


def ask(session, base, payload, timeout):
    started = time.perf_counter()
    response = session.post(base + "/api/v1/kb/qa", json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    assert data["code"] == 0, data
    return {**data["data"], "seconds": round(time.perf_counter() - started, 3)}


def run_case(session, base, common, name, options, expected, allowed, sources, summary, output, policy):
    logger.info("Starting live SAG2 case={}", name)
    result = ask(session, base, {**common, "session_id": name, **options}, policy["budgets"]["http_seconds"])
    checks = check_answer(result, expected, allowed, sources)
    summary["cases"][name] = {"result": result, "checks": checks}
    write_results(output, summary)
    logger.info(
        "Completed live case={} seconds={} backend={} selector={} facts={}",
        name,
        result["seconds"],
        result["retrieval_backend"],
        result["retrieval_strategy"],
        checks["facts"],
    )
    return result


def test_actual_sag2_models_and_browser(client, cli_command, tmp_path, monkeypatch):
    policy = yaml.safe_load(Path(__file__).with_name("sag2_live_acceptance.yaml").read_text(encoding="utf-8"))
    output = Path(os.environ["SAG2_LIVE_OUTPUT"]).resolve()
    assert output.drive.casefold() == "e:", "Live evidence must stay on the requested E drive"
    output.mkdir(parents=True, exist_ok=True)
    runtime_policy = yaml.safe_load(Path(__file__).with_name(policy["runtime_policy"]).read_text(encoding="utf-8"))
    runtime_policy["runtime"]["system_prompt"] = policy["system_prompt"]
    runtime = Hy3Runtime(runtime_policy, output)
    for kind in ("JEV", "RERANK", "EMBEDDING"):
        monkeypatch.setenv(f"KB_{kind}_BASE_URL", "")
        monkeypatch.setenv(f"KB_{kind}_MODEL", "")
    summary = {
        "evidence_kind": policy["evidence_kind"],
        "cases": {},
        "services_stopped": False,
        "generation": "WorkBuddy CLI hy3 (catalog marked free)",
        "embedding": policy["embedding_model"],
        "live_jev": False,
        "live_rerank": False,
    }
    session = requests.Session()
    session.trust_env = False
    process = None
    log = (output / "embedding.log").open("w", encoding="utf-8")
    try:
        with openai_bridge(runtime) as endpoint:
            repo = Repository()
            model = repo.insert(
                "llm_models",
                {
                    "name": "SAG2 live Hy3",
                    "level": "fast",
                    "purpose": "问答",
                    "model_name": "hy3",
                    "base_url": endpoint,
                    "api_key": "",
                    "api_key_env": "",
                    "is_default": 1,
                    "enabled": 1,
                    "timeout_seconds": policy["budgets"]["generation_seconds"],
                    "max_tokens": policy["budgets"]["generation_max_tokens"],
                    "created_at": utc_now_iso(),
                    "updated_at": utc_now_iso(),
                },
            )
            ids, sources = import_sources(session, cli_command.base_url, policy)
            documents = KnowledgeFiles(repo).documents(policy["library"])
            first = SAG2Retrieval(repo).search("银杉计划", documents, "bm25", 10, rounds=1)
            expanded = SAG2Retrieval(repo).search("银杉计划", documents, "bm25", 10, rounds=3)
            summary["bridge"] = {
                "first_document_ids": [row["id"] for row in first[0]],
                "expanded_document_ids": [row["id"] for row in expanded[0]],
                "trace": expanded[1],
            }
            assert ids[1] not in summary["bridge"]["first_document_ids"]
            assert set(ids[:3]).issubset(summary["bridge"]["expanded_document_ids"])
            common = {
                "library_name": policy["library"],
                "question": policy["questions"]["synthesis"],
                "model_id": model["id"],
                "retrieval_backend": "sag2",
                "retrieval_strategy": "bm25",
                "retrieval_rounds": policy["budgets"]["retrieval_rounds"],
                "top_k": 10,
            }
            kwargs = (session, cli_command.base_url, common)
            tail = (summary, output, policy)
            bm25 = run_case(*kwargs, "bm25_synthesis", {}, policy["expectations"]["synthesis"], ids[:4], sources, *tail)
            run_case(
                *kwargs,
                "single_document",
                {"document_id": ids[1], "question": policy["questions"]["single_document"]},
                policy["expectations"]["single_document"],
                [ids[1]],
                sources,
                *tail,
            )
            run_case(
                *kwargs, "unsupported", {"question": policy["questions"]["unsupported"]}, [], ids[:4], sources, *tail
            )
            run_boundaries(session, cli_command.base_url, common, ids, sources, policy, summary)
            assert any(
                phrase in summary["cases"]["unsupported"]["result"]["answer"]
                for phrase in policy["expectations"]["unsupported_patterns"]
            )
            process, embed_base = start_embedding(output, session, policy, log)
            monkeypatch.setenv("KB_EMBEDDING_BASE_URL", embed_base)
            monkeypatch.setenv("KB_EMBEDDING_MODEL", policy["embedding_model"])
            probe = session.post(
                embed_base + "/embeddings", json={"input": ["风险阈值", "风险阈值", "铜材设备"]}, timeout=30
            ).json()
            vectors = [row["embedding"] for row in probe["data"]]
            assert vectors[0] == vectors[1] and vectors[0] != vectors[2] and len(vectors[0]) == 512
            summary["embedding_probe"] = {
                "dimensions": len(vectors[0]),
                "identical_text_equal": True,
                "different_text_differs": True,
            }
            run_case(
                *kwargs,
                "embedding_synthesis",
                {"retrieval_strategy": "embedding"},
                policy["expectations"]["synthesis"],
                ids[:4],
                sources,
                *tail,
            )
            run_case(
                *kwargs,
                "jev_unavailable_embedding_fallback",
                {"retrieval_strategy": "jev"},
                policy["expectations"]["synthesis"],
                ids[:4],
                sources,
                *tail,
            )
            timings = []
            for _ in range(policy["budgets"]["repeat_count"]):
                start = time.perf_counter()
                repeat = SAG2Retrieval(repo).search(policy["questions"]["synthesis"], documents, "bm25", 10, rounds=3)
                timings.append(round((time.perf_counter() - start) * 1000, 3))
                assert repeat[3]["index_reused"]
            summary["cached_bm25_ms"] = {"samples": timings, "median": median(timings)}
            restore_browser(cli_command.base_url, policy, bm25, output)
            summary["browser_original_preview"] = True
            summary["model_calls"] = len(runtime.records)
            write_results(output, summary)
            failures = []
            for name, case in summary["cases"].items():
                if "checks" in case:
                    checks = case["checks"]
                    if not all(value if isinstance(value, bool) else all(value.values()) for value in checks.values()):
                        failures.append(name)
            assert not failures, f"Live acceptance check failures: {failures}"
            assert summary["cases"]["embedding_synthesis"]["result"]["retrieval_strategy"] == "embedding"
            assert summary["cases"]["jev_unavailable_embedding_fallback"]["result"]["fallback_used"]
            summary["passed"] = True
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        log.close()
        session.close()
        summary["services_stopped"] = process is None or process.poll() is not None
        summary["model_calls"] = len(runtime.records)
        write_results(output, summary)


def import_sources(session, base, policy):
    identifiers, sources = [], {}
    for document in [*policy["documents"], policy["isolated_document"], policy["attachment"]]:
        isolated = document == policy["isolated_document"]
        attachment = document == policy["attachment"]
        response = session.post(
            base + "/api/v1/kb/documents",
            data={
                "library_name": policy["isolated_library"] if isolated else policy["library"],
                "attachment_session": "attachment-owner" if attachment else "",
            },
            files={"file": (document["filename"], document["content"].encode("utf-8"))},
            timeout=30,
        ).json()
        assert response["code"] == 0, response
        identifier = response["data"]["doc_id"]
        sources[identifier] = document["content"]
        identifiers.append(identifier)
    return identifiers, sources


def run_boundaries(session, base, common, ids, sources, policy, summary):
    for label in ("isolation", "empty"):
        result = ask(
            session,
            base,
            {**common, "question": policy["questions"][label], "session_id": label},
            policy["budgets"]["http_seconds"],
        )
        assert result["status"] == "no_hits" and not result["references"]
        assert policy["expectations"]["forbidden"] not in result["answer"]
        summary["cases"][label] = {"result": result}
    response = session.post(
        base + "/api/v1/kb/qa",
        json={
            **common,
            "question": policy["questions"]["attachment"],
            "session_id": "attachment-other",
            "document_id": ids[-1],
        },
        timeout=30,
    ).json()
    assert response["code"] != 0
    summary["attachment_foreign_session_rejected"] = True
    result = ask(
        session,
        base,
        {
            **common,
            "question": policy["questions"]["attachment"],
            "session_id": "attachment-owner",
            "document_id": ids[-1],
        },
        policy["budgets"]["http_seconds"],
    )
    summary["cases"]["attachment_owner"] = {
        "result": result,
        "checks": check_answer(result, policy["expectations"]["attachment"], [ids[-1]], sources),
    }


def start_embedding(output, session, policy, log):
    # Reuse the previously installed model environment and server without modifying either.
    manifest = Path(os.environ["SAG2_EMBEDDING_RUNTIME"]).resolve()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [str(manifest / ".venv/Scripts/python.exe"), str(manifest / "embed_server.py")],
        env={**os.environ, "SAG_TEST_EMBED_PORT": str(port), "HF_HUB_OFFLINE": "1"},
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    base = f"http://127.0.0.1:{port}/v1"
    deadline = time.monotonic() + policy["budgets"]["embedding_ready_seconds"]
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Actual embedding process exited before readiness")
        try:
            if session.get(base, timeout=1).status_code == 200:
                return process, base
        except requests.RequestException:
            pass
        time.sleep(0.25)
    process.terminate()
    process.wait(timeout=5)
    raise TimeoutError("Actual embedding service readiness deadline")


def restore_browser(base, policy, result, output):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1600, "height": 1100})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(base + "/app/?module=knowledge&view=qa", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            selector = frame.locator("#rag-library input")
            expect(selector).to_be_visible(timeout=90000)
            selector.click()
            frame.get_by_role("option", name=policy["library"], exact=True).click()
            frame.get_by_text(re.compile("会话与检索设置|Session and Retrieval", re.IGNORECASE)).click()
            frame.get_by_label("会话 ID", exact=True).fill(result["session_id"])
            frame.get_by_role("button", name="恢复此会话", exact=True).click()
            expect(frame.locator("#rag-chat-history")).to_contain_text("QL-2026-1102", timeout=30000)
            page.screenshot(path=str(output / "answer.png"))
            frame.locator("#rag-chat-references").get_by_text("霁蓝回执", exact=True).filter(visible=True).first.click()
            panel = frame.locator(".file-reader-panel-left")
            expect(panel).to_be_visible(timeout=30000)
            expect(panel.frame_locator("iframe").locator("#markdown-preview")).to_contain_text(
                "林岚和周衡", timeout=30000
            )
            page.screenshot(path=str(output / "citation.png"))
        finally:
            browser.close()
