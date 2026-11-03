"""The revised entries work on initial navigation, not just after tab events."""

import pytest

from src.agent.rag import RAGService
from src.frontend.features.learning import adjacent_chapter, chapter_values, curriculum
from src.frontend.services import FrontendService


def test_course_has_content_and_bidirectional_boundaries():
    _, chapters = curriculum()
    assert len(chapters) == 13 and chapters[0]["id"] == "guide"
    assert adjacent_chapter("guide", -1) == "guide"
    assert adjacent_chapter("operations", 1) == "operations"
    for item in chapters:
        text, progress, previous, following = chapter_values(item["id"])
        assert "目标" in text and "前置" in text and "练习" in text and "答案" in text
        assert item["title"] in progress
    with pytest.raises(ValueError):
        chapter_values("../../README.md")


def test_insight_controls_exist_in_initial_configuration(client):
    response = client.get("/app/ai/config")
    assert response.status_code == 200
    labels = [component["props"].get("value") for component in response.json()["components"]]
    assert any("市场复盘" in str(label) for label in labels)
    assert any("个股分析" in str(label) for label in labels)


def test_rag_separates_missing_knowledge_from_model_failure_and_restores_citations(client):
    class Offline:
        def complete(self, prompt, *args, **kwargs):
            from src.knowledge.config import knowledge_config

            if prompt.startswith(knowledge_config()["search"]["planner_prompt"].splitlines()[0]):
                return {"text": '{"keywords":["回撤"],"sufficient":true}', "model": "fixture"}
            raise RuntimeError("offline model")

    empty = RAGService(llm=Offline()).ask({"question": "回撤", "session_id": "no-hits"})
    assert empty["status"] == "no_hits" and not empty["references"]
    note = client.post(
        "/api/v1/kb/notes",
        json={"title": "回撤核对", "content": "回撤是当前净值相对历史峰值的下降。最大回撤反映路径风险。"},
    ).json()
    assert note["code"] == 0
    result = RAGService(llm=Offline()).ask({"question": "回撤", "session_id": "grounding", "scope": "local"})
    assert result["status"] == "model_unavailable" and result["degraded"]
    assert result["references"][0]["doc_id"] == note["data"]["doc_id"]
    assert len(result["references"][0]["content_sha256"]) == 64
    assert result["references"][0]["citation"] == 1
    messages, refs = FrontendService().rag_restore("grounding")
    assert messages[-1]["content"] == result["answer"]
    assert refs.iloc[0]["doc_id"] == note["data"]["doc_id"]
    assert "分块" in FrontendService().rag_index_status()[0]
