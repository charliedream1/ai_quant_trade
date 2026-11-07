"""Each local document maps to a revision-specific source to enforce scope before recall."""

import hashlib

from loguru import logger

from src.core.repository import Repository

from .sag_client import RetrievalUnavailableError, SAGClient, sag_policy


def content_digest(row):
    return hashlib.sha256(str(row.get("content") or "").encode("utf-8")).hexdigest()


class SAGSync:
    def __init__(self, repo=None, client=None):
        self.repo = repo or Repository()
        self.client = client or SAGClient()

    def sync(self, row):
        cfg = self.client.policy
        if not cfg["enabled"]:
            return {"doc_id": row["id"], "status": "disabled"}
        text = str(row.get("content") or "")
        if not text.strip() or len(text) > cfg["max_text_chars"]:
            raise ValueError("Document text is empty or exceeds the SAG synchronization limit")
        digest = content_digest(row)
        values = {
            "sag_content_hash": digest,
            "sag_endpoint_hash": self.client.identity,
            "sag_source_id": "",
            "sag_document_id": "",
            "sag_sync_status": "creating",
        }
        with self.repo.db.transaction():
            current = self.repo.get("kb_documents", row["id"])
            same = (
                current.get("sag_content_hash") == digest and current.get("sag_endpoint_hash") == self.client.identity
            )
            refresh = same and bool(current.get("sag_document_id"))
            if same and not refresh and current.get("sag_sync_status") in {"creating", "ingesting", "uncertain"}:
                raise RetrievalUnavailableError("sync_uncertain_requires_review")
            if not refresh:
                self.repo.update("kb_documents", row["id"], values)
        if refresh:
            return self.refresh(current)
        try:
            source = self.client.create_source(f"{cfg['source_prefix']}:{row['id']}:{digest[:16]}")
            source_id = str(source["id"])
            self.repo.update("kb_documents", row["id"], {"sag_source_id": source_id, "sag_sync_status": "ingesting"})
            document = self.client.ingest(source_id, row["title"], text)
            status = str(document.get("status") or "pending")
            self.repo.update(
                "kb_documents", row["id"], {"sag_document_id": str(document["id"]), "sag_sync_status": status}
            )
            return {"doc_id": row["id"], "status": status}
        except Exception:
            self.repo.update("kb_documents", row["id"], {"sag_sync_status": "uncertain"})
            raise

    def refresh(self, row):
        documents = self.client.documents(str(row["sag_source_id"]))
        if not isinstance(documents, list):
            raise RetrievalUnavailableError("document_status_invalid")
        found = next((item for item in documents if str(item.get("id")) == row["sag_document_id"]), None)
        status = str(found.get("status")) if found else "missing"
        self.repo.update("kb_documents", row["id"], {"sag_sync_status": status})
        return {"doc_id": row["id"], "status": status}


def auto_sync_document(repo, identifier):
    policy = sag_policy()
    if not policy["enabled"] or not policy["auto_sync"]:
        return
    client = SAGClient(policy=policy)
    try:
        row = repo.get("kb_documents", identifier)
        if not row.get("attachment_session"):
            SAGSync(repo, client).sync(row)
    except Exception as exc:
        logger.warning(
            "Optional SAG synchronization incomplete | doc_id={} error_type={}", identifier, type(exc).__name__
        )
    finally:
        client.close()
