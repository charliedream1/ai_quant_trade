"""Exercise scoped SAG ingestion/search, ordinary generation and real semantic fallback HTTP."""

import json
from pathlib import Path

import pytest
import yaml
from playwright.sync_api import expect, sync_playwright

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.config import knowledge_config
from src.knowledge.sag_client import RetrievalUnavailableError, SAGClient
from tests.knowledge.sag_server import sag_server


@pytest.fixture
def sag_values():
    return yaml.safe_load(Path(__file__).with_name("sag_fixtures.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def sag_runtime(client, monkeypatch, sag_values):
    monkeypatch.setenv("ALL_IN_ONE_SAG_ENABLED", "true")
    monkeypatch.setenv("ALL_IN_ONE_SAG_JEV_ENABLED", "false")
    monkeypatch.setenv("ALL_IN_ONE_SAG_TOKEN", "")
    for name in ("KB_RERANK_BASE_URL", "KB_EMBEDDING_BASE_URL"):
        monkeypatch.setenv(name, "")
    with sag_server(sag_values) as (base, state):
        monkeypatch.setenv("ALL_IN_ONE_SAG_BASE_URL", base)
        repo = Repository()
        model = repo.insert(
            "llm_models",
            {
                "name": sag_values["generation_model"],
                "model_name": sag_values["generation_model"],
                "level": "fast",
                "purpose": "问答",
                "base_url": base + "/v1",
                "api_key": "",
                "api_key_env": "",
                "is_default": 1,
                "enabled": 1,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            },
        )
        documents = []
        for item in sag_values["documents"]:
            result = client.post("/api/v1/kb/notes", json={**item, "library_name": sag_values["library"]}).json()
            assert result["code"] == 0, result
            documents.append(result["data"]["doc_id"])
        yield {"base": base, "state": state, "model": model["id"], "documents": documents}


def sync(client, values, document=None):
    payload = {"library_name": values["library"]}
    if document is not None:
        payload["document_id"] = document
    response = client.post("/api/v1/kb/sag/sync", json=payload).json()
    assert response["code"] == 0, response
    return response["data"]


def ask(client, values, runtime, **options):
    return client.post(
        "/api/v1/kb/qa",
        json={
            "library_name": values["library"],
            "question": values["question"],
            "model_id": runtime["model"],
            "retrieval_backend": "sag",
            "session_id": "sag-fixture",
            "retrieval_rounds": 1,
            **options,
        },
    ).json()


def test_real_http_single_document_and_library_qa(client, sag_runtime, sag_values):
    sync(client, sag_values)
    response = ask(client, sag_values, sag_runtime, document_id=sag_runtime["documents"][0])
    assert response["code"] == 0, response
    data = response["data"]
    assert data["status"] == "answered" and data["answer"] == sag_values["answer"]
    assert {ref["doc_id"] for ref in data["references"]} == {sag_runtime["documents"][0]}
    queries = [body for path, body in sag_runtime["state"]["requests"] if path.endswith("/search")]
    assert len(queries[-1]["source_ids"]) == 1 and queries[-1]["strategy"] == "multi"
    result = ask(client, sag_values, sag_runtime)["data"]
    assert {ref["doc_id"] for ref in result["references"]} == set(sag_runtime["documents"])
    assert not result["context_used"]


@pytest.mark.parametrize("failed,expected", [({"multi_jev"}, "multi"), ({"multi_jev", "multi"}, "vector")])
def test_jev_failure_uses_explicit_fallback(client, monkeypatch, sag_runtime, sag_values, failed, expected):
    sync(client, sag_values)
    monkeypatch.setenv("ALL_IN_ONE_SAG_JEV_ENABLED", "true")
    sag_runtime["state"]["fail"] = failed
    result = ask(client, sag_values, sag_runtime)["data"]
    assert result["retrieval_strategy"] == expected and result["degraded"]
    assert result["fallback_reasons"]


@pytest.mark.parametrize("kind", ["embedding", "rerank"])
def test_no_sag_index_uses_standard_semantic_protocol(client, monkeypatch, sag_runtime, sag_values, kind):
    monkeypatch.setenv("KB_" + kind.upper() + "_BASE_URL", sag_runtime["base"] + "/v1")
    monkeypatch.setenv("KB_" + kind.upper() + "_MODEL", sag_values["semantic_model"])
    result = ask(client, sag_values, sag_runtime, document_id=sag_runtime["documents"][0])["data"]
    assert result["retrieval_backend"] == kind and result["status"] == "answered"
    assert {ref["doc_id"] for ref in result["references"]} == {sag_runtime["documents"][0]}


def test_rerank_replaces_jev_on_sag_vector_candidates(client, monkeypatch, sag_runtime, sag_values):
    sync(client, sag_values)
    monkeypatch.setenv("KB_RERANK_BASE_URL", sag_runtime["base"] + "/v1")
    monkeypatch.setenv("KB_RERANK_MODEL", sag_values["semantic_model"])
    result = ask(client, sag_values, sag_runtime, retrieval_strategy="rerank")["data"]
    assert result["retrieval_backend"] == "sag" and result["retrieval_strategy"] == "rerank"


def test_cross_library_and_foreign_provider_evidence_fail_closed(client, sag_runtime, sag_values):
    foreign = client.post(
        "/api/v1/kb/notes", json={"title": "Foreign", "content": "private", "library_name": sag_values["other_library"]}
    ).json()["data"]["doc_id"]
    assert ask(client, sag_values, sag_runtime, document_id=foreign)["code"] != 0
    sync(client, sag_values)
    sag_runtime["state"]["foreign"] = True
    assert ask(client, sag_values, sag_runtime)["code"] != 0


def test_sync_is_idempotent_and_edit_invalidates_remote_evidence(client, sag_runtime, sag_values):
    sync(client, sag_values)
    before = len([path for path, _ in sag_runtime["state"]["requests"] if path.endswith("/ingest")])
    sync(client, sag_values)
    assert len([path for path, _ in sag_runtime["state"]["requests"] if path.endswith("/ingest")]) == before
    repo = Repository()
    identifier = sag_runtime["documents"][0]
    repo.update("kb_documents", identifier, {"content": "Alpha approval revision two"})
    result = ask(client, sag_values, sag_runtime, document_id=identifier)["data"]
    assert result["retrieval_backend"] == "local" and result["fallback_reasons"]


def test_status_excludes_endpoint_tokens_and_does_not_contact_provider(client, sag_runtime, monkeypatch):
    monkeypatch.setenv("ALL_IN_ONE_SAG_TOKEN", "fixture-sensitive-token-value")
    before = len(sag_runtime["state"]["requests"])
    result = client.get("/api/v1/kb/retrieval/status").json()
    assert result["code"] == 0
    assert "fixture-sensitive" not in json.dumps(result) and sag_runtime["base"] not in json.dumps(result)
    assert len(sag_runtime["state"]["requests"]) == before
    assert knowledge_config()["sag"]["auto_sync"] is False


def test_original_model_guided_zvec_remains_independently_selectable(client, sag_runtime, sag_values):
    before = len(sag_runtime["state"]["requests"])
    result = ask(client, sag_values, sag_runtime, retrieval_backend="local", document_id=sag_runtime["documents"][0])
    assert result["code"] == 0, result
    data = result["data"]
    assert data["status"] == "answered" and data["retrieval_backend"] == "local"
    assert data["retrieval_strategy"] == "keywords" and not data["fallback_used"]
    assert data["retrieval_trace"][0]["keywords"] == sag_values["keywords"]
    assert {row["doc_id"] for row in data["references"]} == {sag_runtime["documents"][0]}
    requests = sag_runtime["state"]["requests"][before:]
    assert requests and all(path.endswith("/chat/completions") for path, _ in requests)


def test_pending_index_never_searches_an_empty_or_global_source_scope(client, sag_runtime, sag_values):
    sag_runtime["state"]["pending"] = True
    assert sync(client, sag_values)["items"][0]["status"] == "pending"
    result = ask(client, sag_values, sag_runtime)["data"]
    assert result["retrieval_backend"] == "local"
    assert not [path for path, _ in sag_runtime["state"]["requests"] if path.endswith("/search")]
    for documents in sag_runtime["state"]["sources"].values():
        for document in documents:
            document["status"] = "ready"
    assert all(item["status"] == "ready" for item in sync(client, sag_values)["items"])


def test_uncertain_ingestion_is_not_automatically_repeated(client, sag_runtime, sag_values, monkeypatch):
    def unavailable(*_):
        raise RetrievalUnavailableError("controlled_uncertain_send")

    monkeypatch.setattr(SAGClient, "ingest", unavailable)
    payload = {"library_name": sag_values["library"], "document_id": sag_runtime["documents"][0]}
    for _ in range(2):
        result = client.post("/api/v1/kb/sag/sync", json=payload).json()
        assert result["code"] != 0
    assert len(sag_runtime["state"]["sources"]) == 1


@pytest.mark.parametrize("identifier", [0, -1, True, 1.5])
def test_invalid_document_selector_never_broadens_the_query(client, sag_runtime, sag_values, identifier):
    result = ask(client, sag_values, sag_runtime, document_id=identifier)
    assert result["code"] != 0
    assert not [path for path, _ in sag_runtime["state"]["requests"] if path.endswith("/search")]


def test_private_attachment_cannot_be_indexed_or_queried_by_another_session(client, sag_runtime, sag_values):
    attachment = client.post(
        "/api/v1/kb/documents",
        data={"library_name": sag_values["library"], "attachment_session": "private-session"},
        files={"file": ("private.txt", sag_values["documents"][0]["content"].encode())},
    ).json()["data"]["doc_id"]
    assert ask(client, sag_values, sag_runtime, document_id=attachment)["code"] != 0
    denied = client.post(
        "/api/v1/kb/sag/sync",
        json={"library_name": sag_values["library"], "document_id": attachment, "session_id": "different-session"},
    ).json()
    assert denied["code"] != 0 and not sag_runtime["state"]["sources"]


def test_actual_browser_selects_indexes_and_answers_one_document(
    cli_command, client, sag_runtime, sag_values, tmp_path
):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1100})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=knowledge&view=qa", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            expect(frame.locator("#rag-library input")).to_be_visible(timeout=90000)
            frame.get_by_role("button", name="刷新库名", exact=True).click()
            frame.locator("#rag-library input").click()
            frame.get_by_role("option", name=sag_values["library"], exact=True).click()
            ui = knowledge_config()["qa_ui"]
            for selector, choice in (("#rag-backend", ui["backends"][1][0]), ("#rag-qa-mode", ui["modes"][1][0])):
                frame.locator(selector + " input").click()
                frame.get_by_role("option", name=choice, exact=True).click()
            frame.get_by_role("button", name=ui["refresh_documents"], exact=True).click()
            frame.locator("#rag-document input").click()
            frame.get_by_role("option", name=sag_values["documents"][0]["title"], exact=True).click()
            frame.get_by_role("button", name=ui["sync"], exact=True).click()
            expect(frame.locator("#rag-backend-status")).to_contain_text("ready", timeout=30000)
            frame.get_by_label("问题", exact=True).fill(sag_values["question"])
            frame.get_by_role("button", name="提问", exact=True).click()
            expect(frame.locator("#rag-chat-history")).to_contain_text("17:00", timeout=60000)
            references = frame.locator("#rag-chat-references")
            expect(references).to_contain_text(sag_values["documents"][0]["title"])
            expect(references).not_to_contain_text(sag_values["documents"][1]["title"])
            page.screenshot(path=str(tmp_path / "sag-single-document.png"))
            references.get_by_text(sag_values["documents"][0]["title"], exact=True).filter(visible=True).first.click()
            preview = frame.locator(".file-reader-panel-left")
            expect(preview).to_be_visible(timeout=30000)
            expect(preview.frame_locator("iframe").locator("#markdown-preview")).to_contain_text(
                "AQT-17", timeout=30000
            )
            page.screenshot(path=str(tmp_path / "sag-original-preview.png"))
            history = Repository().db.query_one("SELECT * FROM kb_qa_history ORDER BY id DESC LIMIT 1")
            assert history["qa_scope"] == "document:" + str(sag_runtime["documents"][0])
            assert {item["doc_id"] for item in json.loads(history["cited_docs"])} == {sag_runtime["documents"][0]}
        finally:
            browser.close()
