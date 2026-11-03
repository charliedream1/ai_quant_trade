"""Knowledge frontend service callbacks."""

from __future__ import annotations

import gradio as gr
from src.documents.knowledge import create_category, create_note, delete_document, document_detail
from src.knowledge.config import library_name
from src.knowledge.download import import_url
from src.knowledge.files import KnowledgeFiles

from .foundation import (
    KB_DELETE_CONFIRM_TOKEN,
    Any,
    FTSService,
    RAGService,
    RemoteSourceService,
    Repository,
    compact_json,
    import_uploaded_document,
    json_loads,
    kb_document_source_scope,
    kb_remote_source_id,
    parse_csv,
    parse_json,
    pd,
    require_id,
    require_text,
    to_frame,
    uploaded_file_path,
)
from .rag_chat import RagChatMixin


class KnowledgeServiceMixin(RagChatMixin):
    """Callbacks owned by the knowledge frontend domain."""

    def kb_libraries(self):
        return KnowledgeFiles().libraries()

    def kb_create_library(self, name):
        value = KnowledgeFiles().create_library(require_text(name, "库名"))
        return f"知识库已创建：{value}", gr.update(choices=self.kb_libraries(), value=value)

    def kb_library_choices(self):
        return gr.update(choices=self.kb_libraries())

    def kb_ingest_files(self, files, library, size):
        messages = []
        for value in files or []:
            path = uploaded_file_path(value)
            try:
                row = import_uploaded_document(
                    filename=path.name, content_bytes=path.read_bytes(), library=library, chunk_chars=int(size)
                )
                messages.append(f"{path.name}：已入库，文档 {row['doc_id']}，{row['chunk_count']} 块")
            except Exception as exc:
                messages.append(f"{path.name}：失败，{exc}")
        return "\n\n".join(messages) or "请选择文件", self.kb_library_documents(library)

    def kb_ingest_url(self, url, library, size):
        row = import_url(require_text(url, "网页地址"), library=library, chunk_chars=int(size))
        return f"已入库：{row['title']}，文档 {row['doc_id']}", self.kb_library_documents(library)

    def kb_library_documents(self, library):
        rows = Repository().db.query(
            "SELECT id AS doc_id, title, library_name, source, updated_at FROM kb_documents WHERE library_name = ? AND attachment_session = '' ORDER BY id DESC",
            (library_name(library),),
        )
        return to_frame(rows, ["doc_id", "title", "library_name", "source", "updated_at"])

    def kb_categories(self) -> pd.DataFrame:
        repo = Repository()
        rows = repo.list("kb_categories", order_by="parent_id ASC, sort_order ASC, id ASC")
        for row in rows:
            row["document_count"] = (
                repo.db.scalar("SELECT COUNT(*) FROM kb_documents WHERE category_id = ?", (row["id"],)) or 0
            )
        return to_frame(rows)

    def create_category(self, name: str, parent_id: Any) -> tuple[str, pd.DataFrame]:
        item = create_category({"name": require_text(name, "分类名称"), "parent_id": int(parent_id or 0)})
        return (f"分类已创建，ID={item['category_id']}", self.kb_categories())

    def create_note(self, title: str, category_id: Any, tags: str, content: str) -> tuple[str, pd.DataFrame]:
        item = create_note(
            {
                "title": require_text(title, "笔记标题"),
                "category_id": int(category_id or 0),
                "tags": parse_csv(tags),
                "content": require_text(content, "笔记内容"),
            }
        )
        return (
            f"笔记已保存，文档 ID={item['doc_id']}，分块 {item.get('chunk_count', 0)} 个。",
            self.kb_search("", None, "all"),
        )

    def upload_kb_document(self, file_value: Any, title: str, category_id: Any, tags: str) -> tuple[str, pd.DataFrame]:
        file_path = uploaded_file_path(file_value)
        content = file_path.read_bytes()
        item = import_uploaded_document(
            filename=file_path.name,
            content_bytes=content,
            title=str(title or "").strip() or None,
            category_id=int(category_id or 0),
            tags=tags,
        )
        return (
            f"文档已上传入库，文档 ID={item['doc_id']}，大小 {item['size_bytes']} 字节，分块 {item.get('chunk_count', 0)} 个。",
            self.kb_search("", None, "all"),
        )

    def kb_search(self, keyword: str, category_id: Any, doc_type: str) -> pd.DataFrame:
        repo = Repository()
        category = int(category_id) if category_id not in (None, "", 0) else None
        type_value = None if doc_type in (None, "", "all", "全部") else doc_type
        if str(keyword or "").strip():
            rows = FTSService(repo.db).search_kb(
                str(keyword).strip(), limit=100, category_id=category, doc_type=type_value, scope="all"
            )
            for row in rows:
                row["doc_id"] = row["id"]
                row["source_scope"] = kb_document_source_scope(row)
                row["source_name"] = self._kb_source_name(row, repo)
                row["score"] = 1.0
            return to_frame(rows)
        where: list[str] = []
        params: list[Any] = []
        if category:
            where.append("category_id = ?")
            params.append(category)
        if type_value:
            where.append("doc_type = ?")
            params.append(type_value)
        result = repo.page("kb_documents", 1, 100, " AND ".join(where), params, order_by="updated_at DESC")
        rows = result.get("items") or []
        for row in rows:
            row["doc_id"] = row["id"]
            row["tags"] = json_loads(row.get("tags"), [])
            row["source_scope"] = kb_document_source_scope(row)
            row["source_name"] = self._kb_source_name(row, repo)
            row["chunk_count"] = (
                repo.db.scalar("SELECT COUNT(*) FROM kb_document_chunks WHERE doc_id = ?", (row["id"],)) or 0
            )
        return to_frame(rows)

    def kb_document_detail(self, doc_id: Any) -> str:
        item = document_detail(require_id(doc_id, "文档 ID"), include_content=True)
        tags = item.get("tags") or []
        chunks = item.get("chunks") or []
        chunk_lines = "\n".join(
            f"- #{chunk.get('chunk_index')} {chunk.get('heading') or '正文'}（{chunk.get('char_count', 0)} 字）"
            for chunk in chunks[:8]
        )
        chunk_section = f"\n\n#### 文档分块\n\n{chunk_lines}" if chunk_lines else "\n\n#### 文档分块\n\n暂无分块"
        return f"### {item.get('title', '-')}\n\n- 类型：{item.get('doc_type', '-')}\n- 分类 ID：{item.get('category_id', '-')}\n- 来源：{item.get('source', '-')}\n- 状态：{item.get('status', '-')}\n- 分块数：{item.get('chunk_count', 0)}\n- 标签：{(', '.join(tags) if tags else '-')}\n- 更新时间：{item.get('updated_at', '-')}\n\n{item.get('content') or item.get('summary') or '暂无内容'}{chunk_section}"

    def kb_delete_document(
        self, doc_id: Any, keyword: str, category_id: Any, doc_type: str, confirm_token: str
    ) -> tuple[str, pd.DataFrame, str, str]:
        value = require_id(doc_id, "文档 ID")
        if str(confirm_token or "").strip() != KB_DELETE_CONFIRM_TOKEN:
            raise ValueError(f"删除文档前请在确认框输入 {KB_DELETE_CONFIRM_TOKEN}")
        delete_document(value)
        return (f"文档 {value} 已删除", self.kb_search(keyword, category_id, doc_type), "", "")

    def kb_qa(
        self, question: str, category_id: Any, top_k: Any, session_id: Any = None, reset_context: Any = False
    ) -> tuple[str, pd.DataFrame]:
        result = self._kb_qa_result(question, category_id, top_k, session_id, reset_context)
        return (result.get("answer") or "", to_frame(result.get("references") or []))

    def kb_qa_session(
        self, question: str, category_id: Any, top_k: Any, session_id: Any, reset_context: Any
    ) -> tuple[str, str, pd.DataFrame]:
        result = self._kb_qa_result(question, category_id, top_k, session_id, reset_context)
        status = f"会话 `{result.get('session_id') or 'default'}` 已回答；使用历史 {result.get('context_turns', 0)} 轮；引用 {len(result.get('references') or [])} 条。"
        return (status, result.get("answer") or "", to_frame(result.get("references") or []))

    def kb_qa_clear(self, session_id: Any) -> tuple[str, str, pd.DataFrame]:
        result = RAGService().clear_history({"session_id": session_id})
        return (
            f"会话 `{result.get('session_id') or 'default'}` 已清空 {result.get('deleted', 0)} 条历史。",
            "",
            to_frame([]),
        )

    def kb_qa_sessions(self) -> pd.DataFrame:
        return to_frame(RAGService().list_sessions(limit=50))

    def kb_qa_save_session(self, session_id: Any, name: str, summary: str) -> tuple[str, pd.DataFrame]:
        result = RAGService().update_session({"session_id": session_id, "name": name, "summary": summary})
        return (f"会话 `{result.get('session_id')}` 已保存。", self.kb_qa_sessions())

    def _kb_qa_result(
        self, question: str, category_id: Any, top_k: Any, session_id: Any = None, reset_context: Any = False
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "question": require_text(question, "问题"),
            "top_k": int(top_k or 5),
            "scope": "all",
            "context_turns": 3,
            "session_id": str(session_id or "default").strip() or "default",
            "reset_context": bool(reset_context),
        }
        if category_id not in (None, "", 0):
            payload["category_id"] = int(category_id)
        return RAGService().ask(payload)

    def _kb_source_name(self, row: dict[str, Any], repo: Repository) -> str:
        if kb_document_source_scope(row) != "remote":
            return "本地知识库"
        source_id = kb_remote_source_id(row)
        if source_id:
            source = repo.db.query_one("SELECT name FROM remote_sources WHERE id = ?", (source_id,))
            if source:
                return str(source.get("name") or "远程知识源")
        return "远程知识源"

    def remote_sources(self) -> pd.DataFrame:
        return to_frame(RemoteSourceService().list())

    def create_remote_source(self, name: str, source_type: str, config: str) -> tuple[str, pd.DataFrame]:
        payload = parse_json(config, "连接配置")
        payload.update({"name": require_text(name, "远程知识源名称"), "type": source_type or "feishu"})
        item = RemoteSourceService().create(payload)
        return (f"远程知识源已创建，ID={item['source_id']}", self.remote_sources())

    def test_remote_source(self, source_id: Any) -> str:
        result = RemoteSourceService().test(require_id(source_id, "知识源 ID"))
        return compact_json(result)

    def remote_documents(self, source_id: Any, folder: str, keyword: str = "") -> pd.DataFrame:
        result = RemoteSourceService().documents(
            require_id(source_id, "知识源 ID"),
            str(folder or "").strip() or None,
            str(keyword or "").strip() or None,
            page=1,
            page_size=100,
        )
        return to_frame(result)

    def pull_remote_document(
        self, source_id: Any, remote_doc_id: str, category_id: Any, folder: str = "", library=None, chunk_chars=None
    ) -> tuple[str, pd.DataFrame]:
        payload: dict[str, Any] = {
            "remote_doc_id": require_text(remote_doc_id, "远程文档 ID"),
            "library_name": library,
            "chunk_chars": chunk_chars,
        }
        if category_id not in (None, "", 0):
            payload["category_id"] = int(category_id)
        if str(folder or "").strip():
            payload["folder"] = str(folder).strip()
        result = RemoteSourceService().pull(require_id(source_id, "知识源 ID"), payload)
        return (compact_json(result), self.remote_documents(source_id, folder))

    def sync_remote_documents(
        self, source_id: Any, folder: str, keyword: str, category_id: Any, limit: Any, library=None, chunk_chars=None
    ) -> tuple[str, pd.DataFrame]:
        payload: dict[str, Any] = {
            "folder": str(folder or "").strip(),
            "keyword": str(keyword or "").strip(),
            "limit": int(limit or 20),
            "library_name": library,
            "chunk_chars": chunk_chars,
        }
        if category_id not in (None, "", 0):
            payload["category_id"] = int(category_id)
        result = RemoteSourceService().sync(require_id(source_id, "知识源 ID"), payload)
        return (compact_json(result), self.remote_documents(source_id, folder, keyword))
