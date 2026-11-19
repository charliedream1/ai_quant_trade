"""Context clarifies retrieval while document citations retain their original identity."""

from src.agent.rag import RAGService


def test_page_observations_are_not_document_citations(client, monkeypatch):
    from src.agent.rag import AnswerRetrieval

    seen, generated = [], []
    result = client.post(
        "/api/v1/kb/notes", json={"title": "Declared original", "content": "Original statement: rate is 4.25%."}
    ).json()
    from src.core.repository import Repository

    document = Repository().db.query_one("SELECT * FROM kb_documents ORDER BY id DESC LIMIT 1")

    def retrieve(self, question, *args, **kwargs):
        seen.append(question)
        return [dict(document, snippet="Original statement: rate is 4.25%.")], [], "answered", {"fallback_used": False}

    class LLM:
        def complete(self, prompt, **kwargs):
            generated.append(prompt)
            return {"text": "The page value [P1] differs from original [1].", "model": "declared-context"}

    monkeypatch.setattr(AnswerRetrieval, "run", retrieve)
    envelope = {
        "enabled": True,
        "module": "market",
        "view": "macro",
        "market": "CN",
        "sources": [{"id": "P1", "data": {"rate": 5.0}}],
    }
    response = RAGService(llm=LLM()).ask({"question": "Why the difference?", "page_context": envelope})
    assert '"rate": 5.0' in seen[0] and "P1" in generated[0]
    assert response["references"][0]["citation"] == 1
    assert response["references"][0]["doc_id"] == document["id"]
    stored = Repository().db.query_one("SELECT question FROM kb_qa_history ORDER BY id DESC LIMIT 1")
    assert stored["question"] == "Why the difference?"
    assert result["code"] == 0
