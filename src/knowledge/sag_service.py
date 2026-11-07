"""Explicit indexing and non-network readiness reporting for the knowledge workspace."""

from .files import KnowledgeFiles
from .sag_client import SAGClient, sag_policy
from .sag_sync import SAGSync
from .semantic_ranking import SemanticRanking


def readiness():
    policy = sag_policy()
    return {
        "sag_enabled": policy["enabled"],
        "jev_requested": policy["jev_enabled"],
        "embedding_configured": SemanticRanking("embedding").configured(),
        "rerank_configured": SemanticRanking("rerank").configured(),
        "network_checked": False,
        "strategies": ["auto", "multi_jev", "multi", "vector", "rerank"],
    }


def sync_documents(payload, repo=None):
    files = KnowledgeFiles(repo)
    document_id = payload.get("document_id")
    if document_id is not None and (type(document_id) is not int or document_id <= 0):
        raise ValueError("Document ID must be a positive integer")
    rows = files.documents(
        payload.get("library_name"), session_id=str(payload.get("session_id") or ""), document_id=document_id
    )
    if document_id is not None and not rows:
        raise ValueError("Document is outside the selected library/session")
    if not rows:
        return {"items": []}
    client = SAGClient()
    try:
        if len(rows) > client.policy["sync_batch"]:
            raise ValueError("Select a document or reduce the library to the configured synchronization batch")
        service = SAGSync(files.repo, client)
        return {"items": [service.sync(row) for row in rows]}
    finally:
        client.close()
