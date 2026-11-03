"""Research callback boundary."""

from .base import DomainHandler


class ResearchHandler(DomainHandler):
    domain = "research"
    allowed_methods = frozenset(
        {
            "import_paper_to_kb",
            "download_research_to_kb",
            "list_model_reports",
            "model_report_detail",
            "model_reports",
            "paper_detail",
            "paper_favorite",
            "paper_search_page",
            "research_report_detail",
            "research_reports_page",
            "save_research_report",
        }
    )
