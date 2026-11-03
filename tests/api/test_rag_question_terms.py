"""Natural-language RAG questions keep useful local references."""


def test_rag_question_falls_back_to_meaningful_chinese_terms(client, keyword_model):
    created = client.post(
        "/api/v1/kb/notes",
        json={"title": "RAG自然问句", "content": "回撤是净值相对历史高点的下降。"},
    ).json()
    assert created["code"] == 0

    response = client.post("/api/v1/kb/qa", json={"question": "回撤是什么", "top_k": 3}).json()

    assert response["code"] == 0
    assert response["data"]["references"]
    assert response["data"]["references"][0]["title"] == "RAG自然问句"


def test_question_fallback_preserves_category_and_no_hits(client, keyword_model):
    first = client.post("/api/v1/kb/categories", json={"name": "可读"}).json()["data"]["category_id"]
    second = client.post("/api/v1/kb/categories", json={"name": "隔离"}).json()["data"]["category_id"]
    client.post("/api/v1/kb/notes", json={"title": "风险资料", "category_id": first, "content": "回撤描述风险。"})
    response = client.post(
        "/api/v1/kb/qa",
        json={"question": "回撤是什么", "category_id": second, "reset_context": True},
    ).json()["data"]
    assert not response["references"] and response["status"] == "no_hits"
