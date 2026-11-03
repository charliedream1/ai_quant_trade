"""Knowledge document import helpers."""

from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from markitdown import MarkItDown, StreamInfo

from src.core.exceptions import BusinessError, ErrorCode
from src.core.file_storage import FileStorage
from src.core.kb_chunks import refresh_document_chunks
from src.core.repository import Repository, json_loads
from src.core.timeutil import utc_now_iso
from src.documents.conversion import text_pdf
from src.documents.store import PreviewStore
from src.knowledge.config import chunk_length, knowledge_config, library_name

SUPPORTED_TEXT_EXTENSIONS = {
    ".csv",
    ".htm",
    ".html",
    ".json",
    ".jsonl",
    ".log",
    ".markdown",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
}
SUPPORTED_BINARY_EXTENSIONS = {".doc", ".docx", ".pdf"}
SUPPORTED_EXTENSIONS = set(knowledge_config()["extensions"])
MAX_UPLOAD_BYTES = int(knowledge_config()["max_upload_bytes"])
UPLOAD_SOURCE = "upload"


def import_uploaded_document(
    *,
    filename: str,
    content_bytes: bytes,
    title: str | None = None,
    category_id: int = 0,
    tags: Any = None,
    repo: Repository | None = None,
    storage: FileStorage | None = None,
    library: str | None = None,
    chunk_chars: int | None = None,
    attachment_session: str = "",
    source: str = UPLOAD_SOURCE,
    doc_type: str = "文档",
) -> dict[str, Any]:
    """Import a supported file into local knowledge base."""
    repo = repo or Repository()
    storage = storage or FileStorage()
    name, size = library_name(library), chunk_length(chunk_chars)
    parsed = parse_document_bytes(filename, content_bytes)
    original = PreviewStore().upload(filename, content_bytes, source="knowledge")
    document_title = _document_title(title, filename)
    now = utc_now_iso()
    relative_path = _document_path(storage, document_title)
    storage.write_text(relative_path, parsed["content"])
    tag_values = parse_document_tags(tags)
    row = repo.insert(
        "kb_documents",
        {
            "title": document_title,
            "doc_type": doc_type,
            "category_id": int(category_id or 0),
            "summary": parsed["summary"],
            "content": parsed["content"],
            "file_path": relative_path,
            "source": source,
            "library_name": name,
            "chunk_chars": size,
            "attachment_session": attachment_session,
            "tags": tag_values,
            "status": "ready",
            "imported_at": now,
            "updated_at": now,
            "original_file_id": original["id"],
        },
    )
    row["doc_id"] = row["id"]
    row["tags"] = json_loads(row.get("tags"), [])
    row["size_bytes"] = len(content_bytes)
    row["encoding"] = parsed["encoding"]
    row["original_filename"] = Path(filename or "document").name
    row["chunk_count"] = refresh_document_chunks(
        repo,
        int(row["id"]),
        title=document_title,
        content=parsed["content"],
    )
    original["knowledge_id"] = row["id"]
    PreviewStore().save(original)
    return row


def parse_document_bytes(filename: str, content_bytes: bytes) -> dict[str, str]:
    if not content_bytes:
        raise BusinessError(ErrorCode.INVALID_PARAM, "上传文件为空")
    if len(content_bytes) > MAX_UPLOAD_BYTES:
        raise BusinessError(ErrorCode.INVALID_PARAM, "上传文件超过配置大小限制")
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_EXTENSIONS))
        raise BusinessError(ErrorCode.INVALID_PARAM, f"暂不支持该文件类型，仅支持：{supported}")
    if suffix == ".pdf":
        content = _parse_pdf(content_bytes)
        return {"content": content, "summary": _summary(content), "encoding": "pdf-text"}
    if suffix == ".docx":
        content = _parse_docx(content_bytes)
        return {"content": content, "summary": _summary(content), "encoding": "docx-text"}
    if suffix == ".doc":
        record = PreviewStore().upload(filename, content_bytes, source="knowledge_conversion")
        content = _parse_pdf(text_pdf(record).read_bytes())
        return {"content": content, "summary": _summary(content), "encoding": "doc-text"}
    text, encoding = _decode_text(content_bytes)
    if "\x00" in text:
        raise BusinessError(ErrorCode.PARSE_ERROR, "上传文件疑似二进制内容，暂不支持解析")
    content = _normalize_html(text) if suffix in {".htm", ".html"} else _normalize_text(text)
    if not content.strip():
        raise BusinessError(ErrorCode.PARSE_ERROR, "上传文件未解析出有效文本")
    return {"content": content, "summary": _summary(content), "encoding": encoding}


def parse_document_tags(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BusinessError(ErrorCode.INVALID_PARAM, "标签 JSON 格式错误") from exc
        if not isinstance(parsed, list):
            raise BusinessError(ErrorCode.INVALID_PARAM, "标签 JSON 必须是数组")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in re.split(r"[,，;；\n]+", text) if item.strip()]


def _decode_text(content_bytes: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise BusinessError(ErrorCode.PARSE_ERROR, "上传文件编码无法识别，请使用 UTF-8 或 GB18030")


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _normalize_html(text: str) -> str:
    return _convert_markdown(text.encode("utf-8"), ".html")


def _parse_pdf(content_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise BusinessError(ErrorCode.PARSE_ERROR, "PDF 解析依赖 pypdf 未安装") from exc
    try:
        reader = PdfReader(BytesIO(content_bytes))
        page_texts = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = _normalize_text(page.extract_text() or "")
            if text:
                page_texts.append(f"## 第 {page_number} 页\n\n{text}")
    except Exception as exc:
        raise BusinessError(ErrorCode.PARSE_ERROR, "PDF 文件解析失败") from exc
    content = "\n\n".join(page_texts).strip()
    if not content:
        raise BusinessError(ErrorCode.PARSE_ERROR, "PDF 未提取出文本，扫描件暂不支持 OCR")
    return content


def _parse_docx(content_bytes: bytes) -> str:
    return _convert_markdown(content_bytes, ".docx")


def _convert_markdown(content_bytes: bytes, extension: str) -> str:
    try:
        result = MarkItDown(enable_plugins=False).convert_stream(
            BytesIO(content_bytes), stream_info=StreamInfo(extension=extension)
        )
        content = _normalize_text(result.text_content)
    except Exception as exc:
        raise BusinessError(ErrorCode.PARSE_ERROR, "文档转Markdown失败") from exc
    if not content:
        raise BusinessError(ErrorCode.PARSE_ERROR, "文档未解析出有效文本")
    return content


def _summary(content: str) -> str:
    compact = re.sub(r"\s+", " ", content).strip()
    return compact[:200]


def _document_title(title: str | None, filename: str) -> str:
    clean = str(title or "").strip()
    if clean:
        return clean[:120]
    stem = Path(filename or "未命名文档").stem.strip()
    return (stem or "未命名文档")[:120]


def _document_path(storage: FileStorage, title: str) -> str:
    filename = storage.safe_filename(f"{title}_{uuid4().hex[:8]}", ".md")
    return storage.document_path(filename)
