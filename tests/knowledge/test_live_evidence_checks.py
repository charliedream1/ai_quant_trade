"""Acceptance checks tolerate whitespace normalization but reject altered source text."""

from pathlib import Path

import yaml

from tests.knowledge.test_sag2_live import check_answer


def test_live_citation_audit_preserves_non_whitespace_source_text():
    policy = yaml.safe_load(Path(__file__).with_name("sag2_live_acceptance.yaml").read_text(encoding="utf-8"))
    content = policy["documents"][1]["content"]
    result = {
        "status": "answered",
        "answer": content + " [1]",
        "references": [{"doc_id": 1, "snippet": content.replace("\n", "\n\n")}],
    }
    checks = check_answer(result, policy["expectations"]["single_document"], [1], {1: content})
    assert checks["original_passages"] and checks["valid_citation_numbers"]
    result["references"][0]["snippet"] = content.replace("4.2", "8.5")
    assert not check_answer(result, [], [1], {1: content})["original_passages"]


def test_live_audit_rejects_out_of_range_citation_numbers():
    result = {"status": "answered", "answer": "[2]", "references": [{"doc_id": 1, "snippet": ""}]}
    assert not check_answer(result, [], [1], {1: ""})["valid_citation_numbers"]
