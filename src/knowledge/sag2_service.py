"""Local SAG2 readiness and scoped index preparation without network calls."""

import sqlite3

from src.core.env_file import resolve_env_value

from .config import knowledge_config
from .files import KnowledgeFiles
from .sag2_index import SAG2Index
from .semantic_ranking import SemanticRanking


def readiness():
    cfg = knowledge_config()["sag2"]["jev"]
    with sqlite3.connect(":memory:") as connection:
        try:
            connection.execute("CREATE VIRTUAL TABLE probe USING fts5(body)")
            fts = True
        except sqlite3.OperationalError:
            fts = False
    return {
        "backend": "sag2",
        "fts5_available": fts,
        "network_checked": False,
        "jev_configured": all(resolve_env_value(cfg[key]) for key in ("base_url_env", "model_env")),
        "embedding_configured": SemanticRanking("embedding").configured(),
        "rerank_configured": SemanticRanking("rerank").configured(),
        "strategies": ["auto", "jev", "embedding", "rerank", "bm25"],
    }


def prepare_index(payload, repo=None):
    files = KnowledgeFiles(repo)
    identifier = payload.get("document_id")
    if identifier is not None and (type(identifier) is not int or identifier <= 0):
        raise ValueError("Document ID must be a positive integer")
    rows = files.documents(
        payload.get("library_name"), session_id=str(payload.get("session_id") or ""), document_id=identifier
    )
    if identifier is not None and not rows:
        raise ValueError("Document is outside the selected library/session")
    index = SAG2Index(files.repo, rows)
    try:
        return {
            "backend": "sag2",
            "documents": len(rows),
            "chunks": len(index.rows),
            "index_reused": index.reused,
            "status": "ready",
        }
    finally:
        index.close()
