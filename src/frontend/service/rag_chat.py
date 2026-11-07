"""Chat presentation for file-based keyword retrieval."""

import json
from urllib.parse import urlencode

import gradio as gr
from src.agent.rag import RAGService
from src.core.kb_importer import import_uploaded_document
from src.core.repository import Repository
from src.documents.service import FilePreviewService
from src.documents.view import launcher
from src.knowledge.config import library_name
from src.knowledge.files import KnowledgeFiles
from src.knowledge.sag_service import readiness, sync_documents

from .foundation import ai_console_model_choices, require_text, to_frame, uploaded_file_path


class RagChatMixin:
    def rag_models(self):
        return ai_console_model_choices()

    def rag_chat(
        self,
        question,
        category,
        top_k,
        session,
        scope,
        model,
        library=None,
        rounds=None,
        attachments=None,
        backend="local",
        strategy="auto",
        qa_mode="library",
        document_id=None,
    ):
        name = library_name(library)
        question = require_text(question, "问题")
        imported = []
        for value in attachments or []:
            path = uploaded_file_path(value)
            row = import_uploaded_document(
                filename=path.name,
                content_bytes=path.read_bytes(),
                library=name,
                attachment_session=str(session or "default"),
            )
            imported.append(row["doc_id"])
        if qa_mode == "document" and not document_id:
            if len(imported) != 1:
                raise ValueError("Select one document or attach exactly one new document")
            document_id = imported[0]
        payload = {
            "question": require_text(question, "问题"),
            "category_id": category or None,
            "top_k": int(top_k),
            "session_id": session or "default",
            "scope": scope,
            "library_name": name,
            "retrieval_rounds": rounds,
            "retrieval_backend": backend,
            "retrieval_strategy": strategy,
            "document_id": int(document_id) if qa_mode == "document" and document_id else None,
        }
        if model:
            selected_model = Repository().db.query_one(
                "SELECT id FROM llm_models WHERE enabled=1 AND model_name=?", (model,)
            )
            if selected_model:
                payload["model_id"] = selected_model["id"]
        result = RAGService().ask(payload)
        messages, refs = self.rag_restore(result["session_id"], name, qa_mode, document_id)
        trace = result["retrieval_trace"]
        detail = "；".join(f"第{item['round']}轮：{'、'.join(item['keywords'])}（{item['hits']}条）" for item in trace)
        return (
            f"{result['status']} · {result['retrieval_backend']} / {result['retrieval_strategy']} · 检索{len(trace)}轮 · 引用{len(result['references'])}条\n\n{detail}\n\n"
            + "；".join(result["fallback_reasons"]),
            messages,
            refs,
            "",
            None,
        )

    def rag_restore(self, session, library=None, qa_mode="library", document_id=None):
        if qa_mode == "document" and not document_id:
            return [], to_frame([], ["citation", "doc_id", "title", "chunk_heading", "snippet", "source_name"])
        qa_scope = f"document:{int(document_id)}" if qa_mode == "document" and document_id else ""
        rows = Repository().db.query(
            "SELECT * FROM kb_qa_history WHERE session_id = ? AND library_name = ? AND qa_scope=? ORDER BY id DESC LIMIT 30",
            (session or "default", library_name(library), qa_scope),
        )
        messages = []
        for row in reversed(rows):
            messages.extend(
                [{"role": "user", "content": row["question"]}, {"role": "assistant", "content": row["answer"]}]
            )
        refs = json.loads(rows[0]["cited_docs"]) if rows else []
        return messages, to_frame(refs, ["citation", "doc_id", "title", "chunk_heading", "snippet", "source_name"])

    def rag_documents(self, library, session):
        rows = KnowledgeFiles().documents(library, session_id=session or "default")
        return gr.update(choices=[(row["title"], row["id"]) for row in rows], value=None)

    def rag_retrieval_status(self):
        return readiness()

    def rag_sag_sync(self, library, session, qa_mode, document_id):
        if qa_mode == "document" and not document_id:
            raise ValueError("Select a document first")
        return sync_documents(
            {
                "library_name": library,
                "session_id": session or "default",
                "document_id": int(document_id) if qa_mode == "document" else None,
            }
        )

    def rag_source_preview(self, frame, index):
        selected = frame.iloc[int(index)]
        record = FilePreviewService().knowledge(int(selected["doc_id"]))
        html = launcher(record)
        fragment = urlencode({"side": "left", "quote": str(selected["snippet"]).splitlines()[-1][:100]})
        return html.replace('/view"', "/view#" + fragment + '"')

    def rag_index_status(self):
        repo = Repository()
        documents = repo.db.scalar("SELECT COUNT(*) FROM kb_documents")
        chunks = repo.db.scalar("SELECT COUNT(*) FROM kb_document_chunks")
        choices = [
            (f"{row['name'][:24]} · {row['turn_count']}轮", row["session_id"]) for row in RAGService().list_sessions()
        ]
        return (
            f"已入库 **{documents}** 份资料、**{chunks}** 个分块。使用zvec-grep文件检索，点击引用行可查看原文。",
            gr.update(choices=choices, value=None),
        )
