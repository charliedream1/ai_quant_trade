"""Research frontend service callbacks."""

from __future__ import annotations

from typing import cast

from src.knowledge.research_import import import_research_document

from .contracts import CrossDomainCallbacks
from .foundation import (
    PAPER_COLUMNS,
    REPORT_COLUMNS,
    Any,
    DataSourceManager,
    MarketReportGenerator,
    PaperSearchService,
    Repository,
    _cache_badge,
    _daily_cached,
    _display_now,
    _markdown_link,
    compact_json,
    go,
    json_loads,
    pd,
    require_id,
    resolve_stock_symbol,
    to_frame,
)
from .visuals import (
    paper_distribution_figure,
    report_rating_figure,
)


class ResearchServiceMixin:
    """Callbacks owned by the research frontend domain."""

    def download_research_to_kb(self, kind, identifier, library):
        result = import_research_document(kind, require_id(identifier, "资料 ID"), library)
        return f"原文已下载入库：{result['title']}，文档 {result['doc_id']}"

    def research_reports(self, keyword: str, symbol: str, force_refresh: bool = False) -> pd.DataFrame:
        symbol_value = resolve_stock_symbol(symbol, "股票代码/名称") if str(symbol or "").strip() else ""
        frame, _, _ = _daily_cached(
            ("research_reports", keyword or "", symbol_value),
            lambda: self._build_research_reports(keyword, symbol_value),
            force_refresh=force_refresh,
        )
        return frame

    def research_reports_with_status(
        self, keyword: str, symbol: str, force_refresh: bool = False
    ) -> tuple[str, pd.DataFrame]:
        symbol_value = resolve_stock_symbol(symbol, "股票代码/名称") if str(symbol or "").strip() else ""
        frame, cache_hit, refreshed_at = _daily_cached(
            ("research_reports", keyword or "", symbol_value),
            lambda: self._build_research_reports(keyword, symbol_value),
            force_refresh=force_refresh,
        )
        return f"研报检索完成，共 {len(frame)} 条。{_cache_badge(cache_hit, refreshed_at)}", frame

    def _build_research_reports(self, keyword: str, symbol: str) -> pd.DataFrame:
        items = DataSourceManager().reports(
            keyword=str(keyword or "").strip() or None, symbol=str(symbol or "").strip() or None
        )
        rows = []
        for item in items:
            symbols = item.get("symbols") or []
            summary = item.get("summary") or item.get("body") or f"{item.get('title', '-')}{item.get('pages', '')} 页"
            rows.append(
                {
                    **item,
                    "symbols": ", ".join(symbols) if isinstance(symbols, list) else str(symbols),
                    "summary": summary,
                    "link": _markdown_link(item.get("url")),
                }
            )
        return to_frame(rows, REPORT_COLUMNS)

    def research_reports_page(
        self, keyword: str, symbol: str, force_refresh: bool = False
    ) -> tuple[str, pd.DataFrame, go.Figure]:
        status, frame = self.research_reports_with_status(keyword, symbol, force_refresh)
        return status, frame, report_rating_figure(frame)

    def research_report_detail(self, report_id: Any) -> str:
        detail = DataSourceManager().report_detail(require_id(report_id, "研报 ID"))
        if not detail:
            return "未找到研报详情"
        symbols = detail.get("symbols") or []
        return (
            f"### {detail.get('title', '-')}\n\n"
            f"- 机构：{detail.get('org', '-')}\n"
            f"- 分析师：{detail.get('analyst', '-')}\n"
            f"- 评级：{detail.get('rating', '-')}\n"
            f"- 关联标的：{', '.join(symbols) if symbols else '-'}\n"
            f"- 行业：{detail.get('industry', '-')}\n"
            f"- 日期：{detail.get('publish_date', '-')}\n"
            f"- 来源：{detail.get('source', '-')}\n"
            f"- 链接：{_markdown_link(detail.get('url'))}\n\n"
            f"{detail.get('body') or '暂无正文，原文请查看链接。'}"
        )

    def save_research_report(self, report_id: Any) -> str:
        detail = DataSourceManager().report_detail(require_id(report_id, "研报 ID"))
        if not detail:
            return "未找到研报详情"
        symbols = detail.get("symbols") or []
        content = (
            f"机构：{detail.get('org', '-')}\n"
            f"分析师：{detail.get('analyst', '-')}\n"
            f"评级：{detail.get('rating', '-')}\n"
            f"关联标的：{', '.join(symbols) if symbols else '-'}\n"
            f"日期：{detail.get('publish_date', '-')}\n"
            f"链接：{detail.get('url', '-') or '-'}\n\n"
            f"{detail.get('body') or detail.get('summary') or '暂无正文'}"
        )
        message, _ = cast(CrossDomainCallbacks, self).create_note(
            str(detail.get("title") or f"研报 {report_id}"),
            0,
            "研报,市场分析",
            content,
        )
        return message

    def model_reports(self, report_type: str, topic: str, use_llm: bool) -> tuple[str, pd.DataFrame, str]:
        service = MarketReportGenerator()
        created = service.create(
            {"report_type": report_type or "daily", "topic": topic or "市场综述", "use_llm": bool(use_llm)}
        )
        listed = service.list(page=1, page_size=50)
        report_id = created.get("report_id") or created.get("id")
        if report_id is None:
            raise ValueError("报告生成后缺少报告 ID")
        detail = service.detail(int(report_id))
        return (
            f"报告 {created.get('report_id', created.get('id'))} 已生成",
            to_frame(listed),
            detail.get("content") or compact_json(detail),
        )

    def list_model_reports(self) -> pd.DataFrame:
        return to_frame(MarketReportGenerator().list(page=1, page_size=50))

    def model_report_detail(self, report_id: Any) -> str:
        detail = MarketReportGenerator().detail(require_id(report_id, "报告 ID"))
        return (
            f"### {detail.get('title', '-')}\n\n"
            f"- 类型：{detail.get('report_type', '-')}\n"
            f"- 生成时间：{detail.get('generated_at', '-')}\n\n"
            f"{detail.get('market_summary') or ''}\n\n"
            f"**热门方向**：{', '.join(detail.get('hot_sectors') or []) or '-'}\n\n"
            f"**关键事件**：{', '.join(detail.get('key_events') or []) or '-'}\n\n"
            f"**风险提示**：{detail.get('risk_notice') or '-'}"
        )

    def paper_search(
        self,
        keyword: str,
        source: str,
        year_from: Any,
        year_to: Any,
        refresh: bool = False,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        cache_parts = ("paper_search", keyword or "", source or "", year_from or "", year_to or "")
        if not refresh:
            frame, _, _ = _daily_cached(
                cache_parts,
                lambda: self._build_paper_search(keyword, source, year_from, year_to, refresh=False),
                force_refresh=force_refresh,
            )
            return frame
        return self._build_paper_search(keyword, source, year_from, year_to, refresh=True)

    def paper_search_with_status(
        self,
        keyword: str,
        source: str,
        year_from: Any,
        year_to: Any,
        refresh: bool = False,
        force_refresh: bool = False,
    ) -> tuple[str, pd.DataFrame]:
        cache_parts = ("paper_search", keyword or "", source or "", year_from or "", year_to or "")
        if refresh:
            frame = self._build_paper_search(keyword, source, year_from, year_to, refresh=True)
            return f"论文检索完成，共 {len(frame)} 条。最后刷新 `{_display_now()}`  ·  已同步最新", frame
        frame, cache_hit, refreshed_at = _daily_cached(
            cache_parts,
            lambda: self._build_paper_search(keyword, source, year_from, year_to, refresh=False),
            force_refresh=force_refresh,
        )
        return f"论文检索完成，共 {len(frame)} 条。{_cache_badge(cache_hit, refreshed_at)}", frame

    def paper_search_page(
        self,
        keyword: str,
        source: str,
        year_from: Any,
        year_to: Any,
        refresh: bool = False,
        force_refresh: bool = False,
    ) -> tuple[str, pd.DataFrame, go.Figure]:
        status, frame = self.paper_search_with_status(keyword, source, year_from, year_to, refresh, force_refresh)
        return status, frame, paper_distribution_figure(frame)

    def _build_paper_search(
        self,
        keyword: str,
        source: str,
        year_from: Any,
        year_to: Any,
        refresh: bool = False,
    ) -> pd.DataFrame:
        start = int(year_from) if year_from not in (None, "", 0) else None
        end = int(year_to) if year_to not in (None, "", 0) else None
        result = PaperSearchService().search(
            str(keyword or "").strip(),
            str(source or "").strip() or None,
            start,
            end,
            1,
            30,
            refresh=refresh,
        )
        rows = []
        paper_items = result.get("items") if isinstance(result, dict) else result
        for item in paper_items or []:
            row = dict(item)
            authors = row.get("authors") or []
            row["authors"] = ", ".join(authors) if isinstance(authors, list) else str(authors or "")
            row["link"] = _markdown_link(row.get("url"))
            row["abstract"] = str(row.get("abstract") or "")[:360]
            rows.append(row)
        return to_frame(rows, PAPER_COLUMNS)

    def refresh_papers(self, keyword: str, source: str, year_from: Any, year_to: Any) -> pd.DataFrame:
        return self.paper_search(keyword, source, year_from, year_to, refresh=True)

    def paper_detail(self, paper_id: Any) -> str:
        row = Repository().get("papers", require_id(paper_id, "论文 ID"))
        authors = json_loads(row.get("authors"), [])
        return (
            f"### {row.get('title', '-')}\n\n"
            f"- 作者：{', '.join(authors) if authors else '-'}\n"
            f"- 来源：{row.get('source', '-')}\n"
            f"- 发布时间：{row.get('published_at', '-')}\n"
            f"- 收藏：{'是' if row.get('is_favorite') else '否'}\n"
            f"- 链接：{_markdown_link(row.get('url'))}\n\n"
            f"{row.get('abstract') or '暂无摘要'}"
        )

    def paper_favorite(self, paper_id: Any, note: str, favorite: bool) -> str:
        service = PaperSearchService()
        value = require_id(paper_id, "论文 ID")
        if favorite:
            service.favorite(value, note or "")
            return f"论文 {value} 已收藏"
        service.unfavorite(value)
        return f"论文 {value} 已取消收藏"

    def import_paper_to_kb(self, paper_id: Any, category_id: Any = 0, tags: str = "") -> str:
        item = PaperSearchService().import_to_kb(
            require_id(paper_id, "论文 ID"),
            category_id=int(category_id or 0),
            tags=tags or "论文,市场分析",
        )
        state = "已导入" if item.get("imported") else "已更新"
        return f"论文 {item['paper_id']} {state}知识库，文档 ID={item['doc_id']}"
