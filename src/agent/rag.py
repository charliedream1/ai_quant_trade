"""Knowledge base RAG pipeline."""

import hashlib
import json
from typing import Any

import yaml
from loguru import logger

from src.core.config import PROJECT_ROOT
from src.core.fts import FTSService, kb_document_source_scope, kb_remote_source_id
from src.core.repository import Repository
from src.core.timeutil import utc_now_iso
from src.knowledge.config import knowledge_config, library_name
from src.knowledge.retrieval import RetrievalLoop

from .llm_client import LLMClient

CONTEXT_SNIPPET_CHARS = knowledge_config()["search"]["context_snippet_chars"]
DEFAULT_CONTEXT_TURNS = 3
DEFAULT_QA_SESSION_ID = "default"
MAX_CONTEXT_TURNS = 5
MAX_HISTORY_ANSWER_CHARS = 500
MAX_SESSION_NAME_CHARS = 80
MAX_SESSION_SUMMARY_CHARS = 300
MAX_SESSION_ID_CHARS = 64


class RAGService:
    def __init__(
        self,
        repo: Repository | None = None,
        fts: FTSService | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.repo = repo or Repository()
        self.fts = fts or FTSService()
        self.llm = llm or LLMClient()

    def ask(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = payload.get("question") or ""
        top_k = max(1, min(int(payload.get("top_k") or 5), knowledge_config()["search"]["top_k_max"]))
        library = library_name(payload.get("library_name"))
        raw_category_id = payload.get("category_id")
        category_id: int | None = None
        if raw_category_id is not None and raw_category_id not in ("", 0):
            category_id = int(str(raw_category_id))
        scope = str(payload.get("scope") or "all")
        session_id = _session_id(payload.get("session_id"))
        self._touch_session(session_id, question)
        context_turns = _context_turns(payload.get("context_turns"), reset=bool(payload.get("reset_context")))
        history_rows = self._recent_history(context_turns, session_id=session_id, library=library)
        history_context = self._history_context(history_rows)
        docs, trace, retrieval_status = RetrievalLoop(self.repo, self.llm).run(
            question,
            history_context,
            library=library,
            session_id=session_id,
            limit=top_k,
            rounds=payload.get("retrieval_rounds"),
            category_id=category_id,
            scope=scope,
            model_id=int(payload["model_id"]) if payload.get("model_id") else None,
        )
        context = "\n".join(
            [
                (
                    f"[{index}] [{self._source_name(doc)}] "
                    + doc.get("title", "")
                    + self._chunk_label(doc)
                    + ": "
                    + self._context_text(doc)
                )
                for index, doc in enumerate(docs, start=1)
            ]
        )
        prompt = self._prompt(question, context, history_context)
        config = yaml.safe_load((PROJECT_ROOT / "egs/rag.yaml").read_text(encoding="utf-8"))
        completion = None
        status = retrieval_status
        answer = config.get(retrieval_status, config["no_hits"])
        if docs:
            try:
                options: dict[str, Any] = {"model_id": int(payload["model_id"])} if payload.get("model_id") else {}
                completion = self.llm.complete(prompt, purpose="问答", **options)
                answer, status = completion["text"], "answered"
            except Exception as exc:
                logger.warning("知识问答生成失败 | error={}", type(exc).__name__)
                answer, status = config["model_unavailable"], "model_unavailable"
        refs = [
            {
                "doc_id": doc["id"],
                "title": doc["title"],
                "chunk_id": doc.get("chunk_id"),
                "chunk_index": doc.get("chunk_index"),
                "chunk_heading": doc.get("chunk_heading") or "",
                "snippet": doc.get("snippet") or doc.get("chunk_content") or doc.get("summary") or "",
                "source_scope": kb_document_source_scope(doc),
                "source_name": self._source_name(doc),
                "citation": index,
                "library_name": library,
                "line_number": doc.get("line_number"),
                "retrieval_rounds": len(trace),
                "scope": scope,
                "category_id": category_id,
                "content_sha256": hashlib.sha256(self._context_text(doc).encode("utf-8")).hexdigest(),
            }
            for index, doc in enumerate(docs, start=1)
        ]
        self.repo.insert(
            "kb_qa_history",
            {
                "session_id": session_id,
                "library_name": library,
                "question": question,
                "answer": answer,
                "cited_docs": json.dumps(refs, ensure_ascii=False),
                "model_name": completion["model"] if completion else "no-model",
                "created_at": utc_now_iso(),
            },
        )
        return {
            "answer": answer,
            "references": refs,
            "degraded": status != "answered",
            "status": status,
            "session_id": session_id,
            "library_name": library,
            "retrieval_trace": trace,
            "retrieval_status": retrieval_status,
            "context_used": bool(history_context),
            "context_turns": len(history_rows),
        }

    def clear_history(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = _session_id(payload.get("session_id"))
        cursor = self.repo.db.execute("DELETE FROM kb_qa_history WHERE session_id = ?", (session_id,))
        self._touch_session(session_id, "")
        return {"session_id": session_id, "deleted": cursor.rowcount}

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit or 50), 100))
        return self.repo.db.query(
            """SELECT *
                 FROM (
                       WITH history AS (
                            SELECT session_id,
                                   COUNT(*) AS turn_count,
                                   MAX(id) AS latest_id,
                                   MAX(created_at) AS latest_at
                              FROM kb_qa_history
                             GROUP BY session_id
                       ),
                       latest AS (
                            SELECT h.session_id,
                                   h.turn_count,
                                   h.latest_at,
                                   q.question AS latest_question,
                                   q.answer AS latest_answer
                              FROM history h
                              JOIN kb_qa_history q ON q.id = h.latest_id
                       )
                       SELECT s.session_id,
                              COALESCE(NULLIF(s.name, ''), l.latest_question, s.session_id) AS name,
                              COALESCE(NULLIF(s.summary, ''), SUBSTR(COALESCE(l.latest_answer, l.latest_question, ''), 1, ?)) AS summary,
                              COALESCE(l.turn_count, 0) AS turn_count,
                              COALESCE(l.latest_question, '') AS latest_question,
                              s.created_at AS created_at,
                              COALESCE(s.updated_at, l.latest_at) AS updated_at
                         FROM kb_qa_sessions s
                         LEFT JOIN latest l ON l.session_id = s.session_id
                       UNION ALL
                       SELECT l.session_id,
                              COALESCE(NULLIF(l.latest_question, ''), l.session_id) AS name,
                              SUBSTR(COALESCE(l.latest_answer, l.latest_question, ''), 1, ?) AS summary,
                              l.turn_count AS turn_count,
                              COALESCE(l.latest_question, '') AS latest_question,
                              l.latest_at AS created_at,
                              l.latest_at AS updated_at
                         FROM latest l
                         LEFT JOIN kb_qa_sessions s ON s.session_id = l.session_id
                        WHERE s.session_id IS NULL
                      )
                ORDER BY updated_at DESC
                LIMIT ?""",
            (MAX_SESSION_SUMMARY_CHARS, MAX_SESSION_SUMMARY_CHARS, limit),
        )

    def update_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = _session_id(payload.get("session_id"))
        name = str(payload.get("name") or "").strip()[:MAX_SESSION_NAME_CHARS]
        summary = str(payload.get("summary") or "").strip()[:MAX_SESSION_SUMMARY_CHARS]
        now = utc_now_iso()
        self.repo.db.execute(
            """INSERT INTO kb_qa_sessions(session_id, name, summary, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                    name = excluded.name,
                    summary = excluded.summary,
                    updated_at = excluded.updated_at""",
            (session_id, name, summary, now, now),
        )
        row = self.repo.db.query_one("SELECT * FROM kb_qa_sessions WHERE session_id = ?", (session_id,))
        return row or {"session_id": session_id, "name": name, "summary": summary}

    def _source_name(self, row: dict[str, Any]) -> str:
        if kb_document_source_scope(row) != "remote":
            return "本地知识库"
        source_id = kb_remote_source_id(row)
        if source_id:
            source = self.repo.db.query_one("SELECT name FROM remote_sources WHERE id = ?", (source_id,))
            if source:
                return str(source.get("name") or "远程知识源")
        return "远程知识源"

    def _context_text(self, row: dict[str, Any]) -> str:
        text = str(row.get("chunk_content") or row.get("snippet") or row.get("summary") or "")
        return text[:CONTEXT_SNIPPET_CHARS]

    def _touch_session(self, session_id: str, question: str) -> None:
        now = utc_now_iso()
        title = question.strip()[:MAX_SESSION_NAME_CHARS] or session_id
        summary = question.strip()[:MAX_SESSION_SUMMARY_CHARS]
        self.repo.db.execute(
            """INSERT INTO kb_qa_sessions(session_id, name, summary, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                    updated_at = excluded.updated_at""",
            (session_id, title, summary, now, now),
        )

    def _chunk_label(self, row: dict[str, Any]) -> str:
        heading = str(row.get("chunk_heading") or "").strip()
        index = row.get("chunk_index")
        if heading and index is not None:
            return f" / #{index} {heading}"
        if index is not None:
            return f" / #{index}"
        if heading:
            return f" / {heading}"
        return ""

    def _recent_history(self, limit: int, *, session_id: str, library: str) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        rows = self.repo.db.query(
            """SELECT question, answer, cited_docs, model_name, created_at
                 FROM kb_qa_history
                WHERE session_id = ? AND library_name = ?
                ORDER BY id DESC
                LIMIT ?""",
            (session_id, library, limit),
        )
        return list(reversed(rows))

    def _history_context(self, rows: list[dict[str, Any]]) -> str:
        blocks = []
        for row in rows:
            answer = str(row.get("answer") or "").strip()
            if len(answer) > MAX_HISTORY_ANSWER_CHARS:
                answer = answer[:MAX_HISTORY_ANSWER_CHARS] + "..."
            blocks.append(f"问：{row.get('question') or ''}\n答：{answer}")
        return "\n\n".join(blocks)

    def _prompt(self, question: str, context: str, history_context: str) -> str:
        config = yaml.safe_load((PROJECT_ROOT / "egs/rag.yaml").read_text(encoding="utf-8"))
        return config["prompt"].format(question=question, context=context, history=history_context or "无")


def _context_turns(value: Any, *, reset: bool) -> int:
    if reset:
        return 0
    if value in (None, ""):
        return DEFAULT_CONTEXT_TURNS
    return max(0, min(int(value), MAX_CONTEXT_TURNS))


def _session_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return DEFAULT_QA_SESSION_ID
    return text[:MAX_SESSION_ID_CHARS]
