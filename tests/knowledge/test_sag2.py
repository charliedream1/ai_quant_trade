"""SAG2 multi-hop evidence and real HTTP contracts over explicitly synthetic data."""

from pathlib import Path

import pytest
import yaml
from playwright.sync_api import expect, sync_playwright

from src.agent.llm_client import LLMClient
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.files import KnowledgeFiles
from src.knowledge.sag2_index import SAG2Index
from src.knowledge.sag2_retrieval import SAG2Retrieval
from tests.knowledge.sag2_server import scoring_server


@pytest.fixture
def corpus(client, monkeypatch):
    values = yaml.safe_load(Path(__file__).with_name("sag2_fixtures.yaml").read_text(encoding="utf-8"))
    for kind in ("JEV", "RERANK", "EMBEDDING"):
        monkeypatch.setenv(f"KB_{kind}_BASE_URL", "")
        monkeypatch.setenv(f"KB_{kind}_MODEL", "")
    identifiers = []
    for item in values["documents"]:
        result = client.post("/api/v1/kb/notes", json={**item, "library_name": values["library"]}).json()
        assert result["code"] == 0, result
        identifiers.append(result["data"]["doc_id"])
    return values, identifiers


def retrieve(values, strategy="bm25", rounds=3, **scope):
    repo = Repository()
    docs = KnowledgeFiles(repo).documents(values["library"], **scope)
    return SAG2Retrieval(repo).search(values["question"], docs, strategy, 5, rounds)


def test_evidence_terms_bridge_to_passage_without_original_query(corpus):
    values, ids = corpus
    first, *_ = retrieve(values, rounds=1)
    assert {row["id"] for row in first} == {ids[0]}
    rows, trace, _, meta = retrieve(values, rounds=3)
    assert {row["id"] for row in rows} == set(ids[:2])
    assert len(trace) == 2
    assert "zephyr" in trace[1]["keywords"]
    assert meta["retrieval_backend"] == "sag2" and not meta["fallback_used"]


def test_single_document_and_other_library_do_not_leak(client, corpus):
    values, ids = corpus
    client.post(
        "/api/v1/kb/notes", json={"title": "Orion private", "content": "Orion secret.", "library_name": "other"}
    )
    rows, _, _, _ = retrieve(values, document_id=ids[0])
    assert {row["id"] for row in rows} == {ids[0]}
    assert len(retrieve(values)[0]) == 2


def test_session_attachment_isolation(client, corpus):
    values, ids = corpus
    repo = Repository()
    repo.update("kb_documents", ids[1], {"attachment_session": "owner"})
    assert {row["id"] for row in retrieve(values, session_id="other")[0]} == {ids[0]}
    assert {row["id"] for row in retrieve(values, session_id="owner")[0]} == set(ids[:2])


def test_chinese_recall_and_original_citation(client, corpus):
    values, _ = corpus
    chinese = values["chinese"]
    result = client.post(
        "/api/v1/kb/notes",
        json={"title": chinese["title"], "content": chinese["content"], "library_name": values["library"]},
    ).json()
    rows = retrieve({**values, "question": chinese["question"]})[0]
    assert rows[0]["id"] == result["data"]["doc_id"]
    assert rows[0]["chunk_content"] in chinese["content"]


def test_index_reuse_and_changed_chunk_revision(corpus):
    values, _ = corpus
    repo = Repository()
    docs = KnowledgeFiles(repo).documents(values["library"])
    first = SAG2Index(repo, docs)
    fingerprint = first.fingerprint
    first.close()
    second = SAG2Index(repo, docs)
    assert second.reused
    chunk = next(iter(second.rows.values()))
    second.close()
    repo.db.execute("UPDATE kb_document_chunks SET content=? WHERE id=?", ("Updated text.", chunk["chunk_id"]))
    third = SAG2Index(repo, docs)
    try:
        assert third.fingerprint != fingerprint and not third.reused
    finally:
        third.close()


@pytest.mark.parametrize("strategy", ["jev", "rerank", "embedding"])
def test_real_http_selector_replacement_keeps_bm25_expansion(corpus, monkeypatch, strategy):
    values, ids = corpus
    with scoring_server(values) as (base, state):
        kind = strategy.upper()
        monkeypatch.setenv(f"KB_{kind}_BASE_URL", base + "/decisions" if strategy == "jev" else base)
        monkeypatch.setenv(f"KB_{kind}_MODEL", "protocol-fixture")
        rows, trace, _, meta = retrieve(values, strategy=strategy)
        assert {row["id"] for row in rows} == set(ids[:2])
        assert len(trace) == 2 and meta["retrieval_strategy"] == strategy
        assert not meta["fallback_used"]
        if strategy == "jev":
            second = state["requests"][1][1]
            assert "previously_retrieved_evidence" in second["state"]
            assert all(item["type"] == "noul" for item in second["questions"].values())


def test_unconfigured_auto_has_visible_bm25_fallback(corpus):
    values, _ = corpus
    meta = retrieve(values, strategy="auto")[3]
    assert meta["retrieval_strategy"] == "bm25" and meta["fallback_used"]
    assert any("jev_not_configured" in item for item in meta["fallback_reasons"])


def test_invalid_provider_ids_never_inject_evidence(corpus, monkeypatch):
    values, ids = corpus
    with scoring_server(values) as (base, state):
        state["invalid"] = True
        monkeypatch.setenv("KB_JEV_BASE_URL", base + "/decisions")
        monkeypatch.setenv("KB_JEV_MODEL", "protocol-fixture")
        rows, _, _, meta = retrieve(values, strategy="jev")
        assert {row["id"] for row in rows} == set(ids[:2])
        assert meta["retrieval_strategy"] == "bm25"
        assert "jev:jev_response_invalid" in meta["fallback_reasons"]


def test_real_api_answer_uses_local_citations_and_no_remote_ingestion(client, corpus):
    values, ids = corpus
    with scoring_server(values) as (base, state):
        model = Repository().insert(
            "llm_models",
            {
                "name": "sag2-http-fixture",
                "model_name": "sag2-http-fixture",
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
        prepared = client.post("/api/v1/kb/sag2/index", json={"library_name": values["library"]}).json()
        assert prepared["code"] == 0 and prepared["data"]["chunks"] == 3
        response = client.post(
            "/api/v1/kb/qa",
            json={
                "library_name": values["library"],
                "question": values["question"],
                "model_id": model["id"],
                "retrieval_backend": "sag2",
                "retrieval_strategy": "bm25",
                "retrieval_rounds": 3,
            },
        ).json()
        assert response["code"] == 0, response
        data = response["data"]
        assert data["status"] == "answered" and data["retrieval_backend"] == "sag2"
        assert {row["doc_id"] for row in data["references"]} == set(ids[:2])
        assert "17:00" in data["answer"]
        assert "17:00" in data["references"][1]["snippet"]
        assert "[2]" in data["answer"]
        assert all(path.endswith("chat/completions") for path, _ in state["requests"])


@pytest.mark.parametrize("rounds", [0, -1, 100])
def test_round_limit_is_enforced(corpus, rounds):
    with pytest.raises(ValueError, match="rounds"):
        retrieve(corpus[0], rounds=rounds)


def test_readiness_never_contacts_scoring_provider(client, corpus, monkeypatch):
    with scoring_server(corpus[0]) as (base, state):
        monkeypatch.setenv("KB_JEV_BASE_URL", base + "/decisions")
        monkeypatch.setenv("KB_JEV_MODEL", "fixture")
        result = client.get("/api/v1/kb/retrieval/status").json()["data"]
        assert result["backend"] == "sag2" and result["fts5_available"]
        assert result["jev_configured"] and not result["network_checked"] and state["requests"] == []


def test_browser_sag2_selection_index_question_and_citation(cli_command, corpus, monkeypatch, tmp_path):
    values, _ = corpus
    monkeypatch.setattr(LLMClient, "complete", lambda *args, **kwargs: {"text": values["answer"], "model": "fixture"})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.add_init_script("localStorage.setItem('all-in-one-ui-lang','zh')")
            page.goto(cli_command.base_url + "/app/?module=knowledge&view=qa", wait_until="domcontentloaded")
            frame = page.frame_locator("iframe.workspace-frame.active")
            library = frame.locator("#rag-library input")
            expect(library).to_be_visible(timeout=90000)
            library.click()
            frame.get_by_role("option", name=values["library"], exact=True).click()
            frame.locator("#rag-backend input").click()
            frame.get_by_role("option", name="SAG2 (BM25 with evidence expansion)", exact=True).click()
            frame.locator("#rag-strategy input").click()
            frame.get_by_role("option", name="BM25 only", exact=True).click()
            frame.locator("#rag-sag2-index").click()
            expect(frame.locator("#rag-backend-status")).to_contain_text("ready", timeout=30000)
            frame.get_by_label("问题", exact=True).fill(values["question"])
            frame.get_by_role("button", name="提问", exact=True).click()
            expect(frame.locator("#rag-chat-references")).to_contain_text(
                values["documents"][0]["title"], timeout=30000
            )
            frame.locator("#rag-chat-references").get_by_text(values["documents"][0]["title"], exact=True).filter(
                visible=True
            ).first.click()
            expect(frame.locator(".file-reader-panel-left")).to_be_visible(timeout=30000)
            page.screenshot(path=str(tmp_path / "sag2-citation.png"))
        finally:
            browser.close()
