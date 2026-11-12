"""Provider payload budgets preserve all candidates or fail explicitly."""

import json

import pytest

from src.knowledge.retrieval_http import RetrievalUnavailableError
from src.knowledge.sag2_ranking import EvidenceSelector


def test_decision_batches_keep_every_candidate_within_payload_budget():
    questions = {str(index): {"passage": "evidence " * 20} for index in range(8)}
    batches = list(EvidenceSelector._batches("fixture", {"question": "fixture"}, questions, 500))
    assert len(batches) > 1
    assert [key for batch in batches for key in batch["questions"]] == list(questions)
    assert all(len(json.dumps(batch, ensure_ascii=False)) <= 500 for batch in batches)


def test_oversize_single_candidate_is_never_silently_dropped():
    with pytest.raises(RetrievalUnavailableError, match="budget"):
        list(EvidenceSelector._batches("fixture", {}, {"1": {"passage": "large" * 100}}, 100))
