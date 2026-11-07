"""Knowledge base callback boundary."""

from .base import DomainHandler


class KnowledgeHandler(DomainHandler):
    domain = "knowledge"
    allowed_methods = frozenset(
        {
            "create_remote_source",
            "download_research_to_kb",
            "import_paper_to_kb",
            "kb_create_library",
            "kb_ingest_files",
            "kb_ingest_url",
            "kb_libraries",
            "kb_library_choices",
            "kb_library_documents",
            "learning_detail",
            "learning_tree",
            "list_model_reports",
            "model_report_detail",
            "model_reports",
            "paper_detail",
            "paper_favorite",
            "paper_search_page",
            "pull_remote_document",
            "rag_chat",
            "rag_documents",
            "rag_retrieval_status",
            "rag_sag_sync",
            "rag_index_status",
            "rag_models",
            "rag_restore",
            "rag_source_preview",
            "remote_documents",
            "remote_sources",
            "report_library_list",
            "report_library_open",
            "research_report_detail",
            "research_reports_page",
            "save_research_report",
            "sync_remote_documents",
            "test_remote_source",
        }
    )
