"""The original SAG backend is explicitly retired rather than silently redirected."""

import pytest

from src.knowledge.answer_retrieval import AnswerRetrieval


def test_original_sag_backend_is_rejected():
    with pytest.raises(ValueError, match="retired"):
        AnswerRetrieval(None, None).run("question", "", backend="sag")


def test_original_remote_sync_is_rejected(client):
    result = client.post("/api/v1/kb/sag/sync", json={}).json()
    assert result["code"] != 0
