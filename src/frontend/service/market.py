"""Market frontend service callbacks."""

from __future__ import annotations

from typing import cast

import gradio as gr

from .contracts import CrossDomainCallbacks
from .dashboard_views import (
    _dashboard_kpis_html,
)
from .foundation import (
    FACTOR_ALERT_COLUMNS,
    FACTOR_METRIC_COLUMNS,
    FACTOR_SNAPSHOT_COLUMNS,
    INDEX_COLUMNS,
    NEWS_COLUMNS,
    QLIB_CONFIG_COLUMNS,
    QLIB_RUN_COLUMNS,
    RECOMMEND_COLUMNS,
    RECOMMEND_COMPARE_COLUMNS,
    RECOMMEND_DISPLAY_COLUMNS,
    RECOMMEND_FACTOR_LABELS,
    RECOMMEND_GROUP_SUMMARY_COLUMNS,
    RECOMMEND_GROUP_SYMBOL_COLUMNS,
    RECOMMEND_PLAN_CHOICES,
    RECOMMEND_PLAN_DESCRIPTIONS,
    RECOMMEND_TEMPLATE_COLUMNS,
    RELATION_EDGE_COLUMNS,
    RELATION_NODE_COLUMNS,
    RELATION_PATH_COLUMNS,
    RESOURCE_POOL_COLUMNS,
    RESOURCE_POOL_ITEM_COLUMNS,
    SECTOR_COLUMNS,
    SECURITY_MASTER_COLUMNS,
    WATCHLIST_COLUMNS,
    WATCHLIST_GROUP_COLUMNS,
    Any,
    BacktestRunner,
    DataSourceManager,
    FactorMonitorService,
    NewsAggregator,
    QlibWorkflowService,
    QuoteService,
    Recommender,
    RelationGraphService,
    Repository,
    ResourcePoolService,
    SecurityMasterService,
    Sequence,
    StockAnalyzer,
    _cache_badge,
    _compact_mapping,
    _daily_cached,
    _display_now,
    _recommend_records,
    compact_json,
    get_settings,
    go,
    json,
    json_loads,
    parse_csv,
    parse_json,
    parse_stock_symbols,
    pd,
    require_id,
    require_text,
    resolve_stock_symbol,
    styled_frame,
    to_frame,
    uploaded_file_path,
    utc_now_iso,
)
from .relation_layout import evidence_html, plot_metadata
from .visuals import (
    _format_display_time,
    _safe_float,
    factor_correlation_figure,
    factor_diagnostic_figure,
    factor_ic_figure,
    factor_quantile_figure,
    factor_quantile_history_figure,
    factor_style_exposure_figure,
    keyword_figure,
    kline_figure,
    market_bar_figure,
    recommend_factor_figure,
    recommend_group_compare_figure,
    relation_analysis_frame,
    relation_figure,
    relation_summary_markdown,
    score_figure,
)


class MarketServiceMixin:
    """Callbacks owned by the market frontend domain."""

    def relation_evidence_options(self, figure: Any) -> dict[str, Any]:
        meta = plot_metadata(figure)
        edges = (meta or {}).get("relation_edges") or []
        return gr.update(
            choices=[
                (
                    f"{index + 1}. {row['source']} → {row['target']} · {row.get('relation_label') or row.get('relation_type')}",
                    str(index),
                )
                for index, row in enumerate(edges)
            ],
            value=None,
        )

    def relation_evidence_detail(self, figure: Any, selected: str) -> str:
        meta = plot_metadata(figure)
        edges = (meta or {}).get("relation_edges") or []
        if selected is None or not str(selected).isdigit() or int(selected) >= len(edges):
            return "<p>请选择一条关系查看来源、原文与匹配依据。</p>"
        return evidence_html(edges[int(selected)])

    def relation_fit(self, figure: Any) -> go.Figure:
        meta = plot_metadata(figure)
        nodes = (meta or {}).get("relation_nodes") or []
        edges = (meta or {}).get("relation_edges") or []
        center = next((str(row["id"]) for row in nodes if row.get("is_center")), str(nodes[0]["id"]) if nodes else "")
        return relation_figure(nodes, edges, center)

    def market_overview(self, board: str, limit: Any) -> tuple[Any, Any, go.Figure]:
        quotes = QuoteService()
        limit_value = max(1, min(int(limit or 20), 100))
        indices = quotes.indices(refresh=True)
        sectors = quotes.sectors(board=board or "industry", limit=limit_value)
        return (
            styled_frame(indices, INDEX_COLUMNS, gradient=["change_pct"]),
            styled_frame(sectors, SECTOR_COLUMNS, gradient=["change_pct"]),
            market_bar_figure(sectors),
        )

    def factor_default_universe(self) -> str:
        return FactorMonitorService().default_universe_text()

    def factor_monitor_summary(
        self,
        universe_text: str = "",
        force_refresh: bool = False,
    ) -> tuple[str, str, go.Figure, go.Figure, go.Figure, go.Figure, go.Figure]:
        payload, cache_hit, refreshed_at = self._factor_monitor_payload(universe_text, force_refresh)
        status = f"{payload.get('status', '因子监控已刷新')}  ·  {_cache_badge(cache_hit, refreshed_at)}"
        return (
            status,
            _dashboard_kpis_html(payload.get("kpis") or []),
            factor_ic_figure(payload.get("ic_history") or []),
            factor_quantile_figure(payload.get("quantile_returns") or []),
            factor_diagnostic_figure(payload.get("ic_decay") or [], payload.get("metrics") or []),
            factor_quantile_history_figure(payload.get("quantile_history") or []),
            factor_style_exposure_figure(payload.get("style_exposure") or []),
        )

    def factor_monitor_details(
        self,
        universe_text: str = "",
        force_refresh: bool = False,
    ) -> tuple[Any, pd.DataFrame, Any, go.Figure, str]:
        payload, _, _ = self._factor_monitor_payload(universe_text, force_refresh)
        qlib = payload.get("qlib") or {}
        qlib_markdown = (
            f"**Qlib状态**：`{qlib.get('status', '-')}`  ·  "
            f"版本 `{qlib.get('version', '-')}`  ·  许可证 `{qlib.get('license', '-')}`\n\n"
            f"{qlib.get('next_step', '')}"
        )
        return (
            styled_frame(
                payload.get("metrics") or [],
                FACTOR_METRIC_COLUMNS,
                gradient=["rank_ic_mean", "ic", "icir", "hit_rate", "long_short_return"],
            ),
            to_frame(payload.get("alerts") or [], FACTOR_ALERT_COLUMNS),
            styled_frame(
                payload.get("snapshots") or [],
                FACTOR_SNAPSHOT_COLUMNS,
                gradient=["value", "change_pct"],
            ),
            factor_correlation_figure(payload.get("correlation") or {}),
            qlib_markdown,
        )

    def qlib_workflow_defaults(self) -> tuple[str, str, str]:
        config = QlibWorkflowService().config()
        params = {
            "experiment_name": config.get("experiment_name") or "all_in_one_qlib_research",
            "market": config.get("market") or "",
            "benchmark": config.get("benchmark") or "",
            "region": config.get("region") or "",
            "artifact_dir": config.get("artifact_dir") or "",
        }
        return (
            str(config.get("workflow_path") or ""),
            str(config.get("provider_uri") or ""),
            compact_json(params),
        )

    def qlib_workflow_status(self, run_type: str = "") -> tuple[str, pd.DataFrame, pd.DataFrame]:
        service = QlibWorkflowService()
        payload = service.status()
        diagnostic = payload.get("diagnostic") or {}
        config = payload.get("config") or {}
        status = (
            f"**Qlib实验状态**：`{payload.get('status')}`  ·  "
            f"环境 `{diagnostic.get('status', '-')}`  ·  版本 `{diagnostic.get('version', '-')}`\n\n"
            f"{payload.get('next_step', '')}"
        )
        config_rows = [
            {"item": "config_path", "value": payload.get("config_path") or "-", "note": "当前读取的配置文件"},
            {"item": "provider_uri", "value": config.get("provider_uri") or "-", "note": "Qlib 数据目录"},
            {"item": "workflow_path", "value": config.get("workflow_path") or "-", "note": "Qlib workflow YAML"},
            {"item": "experiment_name", "value": config.get("experiment_name") or "-", "note": "实验名称"},
            {"item": "market", "value": config.get("market") or "-", "note": "股票池/市场"},
            {"item": "benchmark", "value": config.get("benchmark") or "-", "note": "基准"},
        ]
        return status, to_frame(config_rows, QLIB_CONFIG_COLUMNS), self.qlib_workflow_runs(run_type)

    def qlib_workflow_create_run(
        self,
        run_type: str,
        workflow_path: str,
        provider_uri: str,
        params: str,
    ) -> tuple[str, pd.DataFrame]:
        run = QlibWorkflowService().create_run(
            {
                "run_type": run_type or "workflow",
                "workflow_path": workflow_path,
                "provider_uri": provider_uri,
                "params": parse_json(params, "Qlib 运行参数"),
            }
        )
        message = f"Qlib运行记录 {run['run_id']} 已处理，状态 `{run['status']}`"
        metrics = run.get("metrics") or {}
        if metrics.get("returncode") is not None:
            message += f"  ·  qrun返回码 `{metrics.get('returncode')}`"
        if run.get("error_msg"):
            message += f"\n\n{run['error_msg']}"
        return message, self.qlib_workflow_runs(run_type)

    def qlib_workflow_runs(self, run_type: str = "") -> pd.DataFrame:
        selected_type = str(run_type or "").strip() or None
        result = QlibWorkflowService().list_runs(run_type=selected_type, page=1, page_size=100)
        rows = []
        for item in result.get("items") or []:
            row = dict(item)
            row["training_metric_summary"] = _compact_mapping(row.get("training_metrics") or {})
            row["portfolio_metric_summary"] = _compact_mapping(row.get("portfolio_metrics") or {})
            rows.append(row)
        return to_frame(rows, QLIB_RUN_COLUMNS)

    def backtest_engines(self) -> pd.DataFrame:
        return to_frame(BacktestRunner().engines())

    def _factor_monitor_payload(
        self,
        universe_text: str,
        force_refresh: bool = False,
    ) -> tuple[dict[str, Any], bool, str]:
        normalized = ",".join(parse_csv(universe_text)) or "default"
        return _daily_cached(
            ("factor_monitor", normalized),
            lambda: FactorMonitorService().monitor(universe_text=universe_text or "", force_refresh=force_refresh),
            force_refresh=force_refresh,
        )

    def watchlist_groups(self) -> pd.DataFrame:
        return to_frame(QuoteService().list_watchlist_groups(), WATCHLIST_GROUP_COLUMNS)

    def create_watchlist_group(self, name: str, sort_order: Any) -> tuple[str, pd.DataFrame]:
        item = QuoteService().create_group(require_text(name, "分组名称"), int(sort_order or 0))
        return f"自选分组已创建，ID={item['id']}", self.watchlist_groups()

    def add_watchlist_symbols(self, group_id: Any, symbols: str) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        service = QuoteService()
        value = self._ensure_watchlist_group(service, group_id)
        parsed = parse_stock_symbols(require_text(symbols, "股票代码/名称"))
        if not parsed:
            raise ValueError("请输入有效的股票代码、名称、拼音或别名")
        result = service.add_symbols(value, parsed)
        return (
            f"已加入 {len(result.get('added') or [])} 只标的到分组 {value}",
            self.watchlist_groups(),
            to_frame(service.watchlist_quotes(value), WATCHLIST_COLUMNS),
        )

    def security_master_search(self, query: str, limit: Any = 20) -> pd.DataFrame:
        rows = SecurityMasterService().search(query, limit=int(limit or 20))
        return to_frame(rows, SECURITY_MASTER_COLUMNS)

    def resource_pools(self) -> pd.DataFrame:
        rows = ResourcePoolService().list_pools()
        return to_frame(rows, RESOURCE_POOL_COLUMNS)

    def resource_pool_items(self, pool_id: Any) -> pd.DataFrame:
        value = self._optional_resource_pool_id(pool_id)
        rows = ResourcePoolService().list_items(value)
        return to_frame(rows, RESOURCE_POOL_ITEM_COLUMNS)

    def create_resource_pool(self, name: str, description: str) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        service = ResourcePoolService()
        pool = service.create_pool(name, description, "manual")
        return (
            f"资源池 `{pool['name']}` 已保存，ID={pool['id']}",
            self.resource_pools(),
            to_frame(service.list_items(int(pool["id"])), RESOURCE_POOL_ITEM_COLUMNS),
        )

    def add_resource_pool_symbols(
        self,
        pool_id: Any,
        symbols: str,
        remark: str,
        weight: Any,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        service = ResourcePoolService()
        result = service.add_symbols(
            self._optional_resource_pool_id(pool_id),
            require_text(symbols, "资源池标的"),
            source="manual",
            remark=str(remark or "").strip(),
            weight=_safe_float(weight, 1.0),
        )
        return (
            f"资源池 {result['pool_id']} 已更新：新增 {result['added']}，更新 {result['updated']}，跳过 {result['skipped']}",
            self.resource_pools(),
            to_frame(service.list_items(int(result["pool_id"])), RESOURCE_POOL_ITEM_COLUMNS),
        )

    def import_resource_pool_file(
        self,
        pool_id: Any,
        file_value: Any,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        service = ResourcePoolService()
        result = service.import_file(self._optional_resource_pool_id(pool_id), uploaded_file_path(file_value))
        return (
            f"已导入 `{result['file_name']}` 到资源池 {result['pool_id']}："
            f"新增 {result['added']}，更新 {result['updated']}，跳过 {result['skipped']}",
            self.resource_pools(),
            to_frame(service.list_items(int(result["pool_id"])), RESOURCE_POOL_ITEM_COLUMNS),
        )

    def add_recommendations_to_resource_pool(
        self,
        pool_id: Any,
        recommend_rows: Any,
        fallback_symbols: str,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        records = _recommend_records(recommend_rows)
        symbols = [str(row.get("symbol") or "") for row in records if row.get("symbol")]
        if not symbols:
            symbols = parse_stock_symbols(fallback_symbols)
        if not symbols:
            raise ValueError("推荐结果为空，请先生成推荐或输入股票池")
        service = ResourcePoolService()
        result = service.add_symbols(
            self._optional_resource_pool_id(pool_id),
            ",".join(symbols[:30]),
            source="recommendation",
            remark="来自股票推荐页",
        )
        return (
            f"推荐候选已加入资源池 {result['pool_id']}：新增 {result['added']}，更新 {result['updated']}，候选 {len(symbols[:30])}",
            self.resource_pools(),
            to_frame(service.list_items(int(result["pool_id"])), RESOURCE_POOL_ITEM_COLUMNS),
        )

    def resource_pool_to_universe(self, pool_id: Any) -> tuple[str, str, pd.DataFrame]:
        service = ResourcePoolService()
        value = self._optional_resource_pool_id(pool_id)
        items = service.list_items(value)
        symbols = [str(item.get("symbol") or "") for item in items if item.get("symbol")]
        if not symbols:
            raise ValueError("资源池为空，请先添加标的")
        selected_pool_id = int((items[0] or {}).get("pool_id") or value or 0)
        return (
            f"已载入资源池 {selected_pool_id}，共 {len(symbols)} 只标的",
            ",".join(symbols),
            to_frame(items, RESOURCE_POOL_ITEM_COLUMNS),
        )

    @staticmethod
    def _optional_resource_pool_id(value: Any) -> int | None:
        if value in (None, "", 0, "0"):
            return None
        return require_id(value, "资源池 ID")

    def remove_watchlist_symbol(self, group_id: Any, symbol: str) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        value = require_id(group_id, "分组 ID")
        text = resolve_stock_symbol(symbol, "股票代码/名称")
        service = QuoteService()
        service.remove_symbol(value, text)
        return (
            f"已从分组 {value} 删除 {text}",
            self.watchlist_groups(),
            to_frame(service.watchlist_quotes(value), WATCHLIST_COLUMNS),
        )

    def news(
        self,
        category: str,
        keyword: str,
        source: str,
        refresh: bool = False,
        force_refresh: bool = False,
    ) -> tuple[pd.DataFrame, go.Figure, str]:
        cache_parts = ("news", category or "", keyword or "", source or "", bool(refresh))
        if not refresh:
            payload, cache_hit, refreshed_at = _daily_cached(
                cache_parts,
                lambda: self._build_news(category, keyword, source, refresh=False),
                force_refresh=force_refresh,
            )
            return payload[0], payload[1], f"{payload[2]}  ·  {_cache_badge(cache_hit, refreshed_at)}"
        payload = self._build_news(category, keyword, source, refresh=True)
        return payload[0], payload[1], f"{payload[2]}  ·  最后刷新 `{_display_now()}`  ·  已同步最新"

    def _build_news(
        self,
        category: str,
        keyword: str,
        source: str,
        refresh: bool = False,
    ) -> tuple[pd.DataFrame, go.Figure, str]:
        category_value = None if category in (None, "", "全部") else category
        source_value = str(source or "").strip() or None
        aggregator = NewsAggregator()
        result = aggregator.list_news(
            category_value,
            str(keyword or "").strip() or None,
            source_value,
            1,
            30,
            refresh=refresh,
        )
        cloud = aggregator.keyword_cloud("day", category_value, 30)
        return (
            to_frame(result, NEWS_COLUMNS),
            keyword_figure(cloud),
            f"共找到 {result.get('total', 0)} 条新闻",
        )

    def refresh_news(self, category: str, keyword: str, source: str) -> tuple[pd.DataFrame, go.Figure, str]:
        return self.news(category, keyword, source, refresh=True)

    def news_detail(self, news_id: Any) -> str:
        row = Repository().get("news_items", require_id(news_id, "新闻 ID"))
        keywords = json_loads(row.get("keywords"), [])
        return (
            f"### {row.get('title', '-')}\n\n"
            f"- 来源：{row.get('source', '-')}\n"
            f"- 分类：{row.get('category', '-')}\n"
            f"- 发布时间：{row.get('published_at', '-')}\n"
            f"- 关键词：{', '.join(keywords) if keywords else '-'}\n"
            f"- 链接：{row.get('url', '-')}\n\n"
            f"{row.get('summary') or '暂无摘要'}"
        )

    def stock(
        self,
        symbol: str,
        period: str,
        count: Any,
    ) -> tuple[str, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame, pd.DataFrame]:
        symbol_value = resolve_stock_symbol(symbol, "股票代码/名称")
        result = StockAnalyzer().detail(symbol_value, "", period or "daily", int(count or 60))
        quote = result.get("quote") or {}
        change = float(quote.get("change_pct") or 0)
        summary = (
            f"### {quote.get('name', symbol_value)} `{symbol_value}`\n"
            f"现价 **{quote.get('latest_price', '-')}**　涨跌幅 **{change:.2f}%**　"
            f"换手率 **{quote.get('turnover_rate', '-')}%**　数据源 `{quote.get('data_source', '-')}`"
        )
        finance = [{"指标": key, "数值": value} for key, value in (result.get("finance") or {}).items()]
        return (
            summary,
            score_figure(result.get("score") or {}),
            to_frame(finance, ["指标", "数值"]),
            kline_figure(result.get("kline") or [], symbol_value),
            to_frame(result.get("news") or [], NEWS_COLUMNS),
            to_frame(result.get("reports") or []),
        )

    def add_stock_to_watchlist(self, symbol: str, group_id: Any) -> tuple[str, pd.DataFrame]:
        service = QuoteService()
        value = self._ensure_watchlist_group(service, group_id)
        symbols = parse_stock_symbols(require_text(symbol, "股票代码/名称"))
        if not symbols:
            raise ValueError("请输入有效的股票代码、名称、拼音或别名")
        result = service.add_symbols(value, symbols[:1])
        return (
            f"已加入自选：{', '.join(result.get('added') or []) or '无新增'}",
            to_frame(service.watchlist_quotes(value), WATCHLIST_COLUMNS),
        )

    def _ensure_watchlist_group(self, service: QuoteService, group_id: Any) -> int:
        value = int(group_id or 0)
        if value > 0:
            return value
        groups = service.list_watchlist_groups()
        return int(groups[0]["id"]) if groups else int(service.create_group("默认自选", 0)["id"])

    def relations(
        self,
        symbol: str,
        depth: Any,
        relation_types: Sequence[str] | None = None,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, go.Figure]:
        symbol_value = resolve_stock_symbol(symbol, "股票代码/名称")
        selected_types = [str(item) for item in relation_types or [] if str(item or "").strip()]
        depth_value = int(depth or 1)
        result, cache_hit, refreshed_at = _daily_cached(
            ("relations", symbol_value, depth_value, ",".join(sorted(selected_types))),
            lambda: RelationGraphService().graph(symbol_value, selected_types or None, depth_value),
        )
        data = DataSourceManager()
        quote = data.stock_quote(symbol_value)
        sector_by_code = {item["code"]: item for item in data.sectors(limit=100)}
        nodes = []
        for item in result.get("nodes") or []:
            node = dict(item)
            node_id = str(node.get("id"))
            if node_id == symbol_value:
                node.update(
                    name=quote.get("name") or node_id,
                    type="stock",
                    change_pct=quote.get("change_pct") or 0,
                )
            elif node_id in sector_by_code:
                sector = sector_by_code[node_id]
                node.update(
                    name=sector.get("name") or node_id,
                    type="sector",
                    change_pct=sector.get("change_pct") or 0,
                )
            nodes.append(node)
        edges = result.get("edges") or []
        summary = result.get("summary") or {}
        return (
            f"{relation_summary_markdown(summary, selected_types)}\n\n> {_cache_badge(cache_hit, refreshed_at)}",
            relation_analysis_frame(summary),
            to_frame(summary.get("layer_paths") or [], RELATION_PATH_COLUMNS),
            to_frame(nodes, RELATION_NODE_COLUMNS),
            to_frame(edges, RELATION_EDGE_COLUMNS),
            relation_figure(nodes, edges, symbol_value),
        )

    def export_relations(self, symbol: str, depth: Any, relation_types: Sequence[str] | None = None) -> tuple[str, str]:
        symbol_value = resolve_stock_symbol(symbol, "股票代码/名称")
        summary, analysis, paths, nodes, edges, _ = self.relations(symbol_value, depth, relation_types)
        exported_at = utc_now_iso()
        export_dir = get_settings().data_dir / "reports" / "relations" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = exported_at.replace(":", "").replace("-", "").replace("Z", "")
        export_path = export_dir / f"relation_graph_{symbol_value}_{timestamp}.json"
        payload = {
            "symbol": symbol_value,
            "depth": int(depth or 1),
            "relation_types": [str(item) for item in relation_types or [] if str(item or "").strip()],
            "exported_at": exported_at,
            "summary_markdown": summary,
            "analysis": analysis.to_dict(orient="records"),
            "paths": paths.to_dict(orient="records"),
            "nodes": nodes.to_dict(orient="records"),
            "edges": edges.to_dict(orient="records"),
        }
        export_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"关系图谱已导出：`{export_path}`", str(export_path)

    def stock_to_relations(
        self,
        symbol: str,
        depth: Any,
        relation_types: Sequence[str] | None = None,
    ) -> tuple[str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, go.Figure]:
        selected_symbol = resolve_stock_symbol(symbol, "股票代码/名称")
        summary, analysis, paths, nodes, edges, figure = self.relations(selected_symbol, depth, relation_types)
        return f"已同步 {selected_symbol} 到关系图谱", selected_symbol, summary, analysis, paths, nodes, edges, figure

    def recommend(self, plan: str, path: str, limit: float, universe_text: str) -> tuple[str, pd.DataFrame]:
        symbols = parse_stock_symbols(universe_text)
        count = max(1, min(int(limit or 10), 30))
        payload: dict[str, Any] = {
            "path": path or "quick",
            "plan": plan or "balanced",
            "count": count,
        }
        if symbols:
            payload["universe"] = {"symbols": symbols}
        task = Recommender().create_task(payload)
        result = Recommender().result(int(task["task_id"]))
        rows = self._recommend_display_rows(result, plan or "balanced")
        description = RECOMMEND_PLAN_DESCRIPTIONS.get(plan or "balanced", "综合候选方案。")
        frame = to_frame(rows, RECOMMEND_COLUMNS)
        if not frame.empty and "selected_at" in frame.columns:
            frame["selected_at"] = frame["selected_at"].map(_format_display_time)
        return f"任务 {task['task_id']} 已完成，共返回 {len(result)} 个候选。方案说明：{description}", frame.rename(
            columns=RECOMMEND_DISPLAY_COLUMNS
        )

    def _recommend_display_rows(self, result: Sequence[dict[str, Any]], plan: str) -> list[dict[str, Any]]:
        plan_labels = {value: label for label, value in RECOMMEND_PLAN_CHOICES}
        plan_label = plan_labels.get(plan or "balanced", plan or "balanced")
        rows: list[dict[str, Any]] = []
        for item in result:
            row = dict(item)
            factors = row.pop("factors", {}) or {}
            row["plan"] = plan_label
            row["momentum"] = round(_safe_float(factors.get("momentum")), 2)
            row["liquidity"] = round(_safe_float(factors.get("liquidity")), 2)
            row["sentiment"] = round(_safe_float(factors.get("sentiment")), 2)
            row["chan"] = round(_safe_float(factors.get("chan")), 2) if factors.get("chan") is not None else "-"
            rows.append(row)
        return rows

    def recommend_condition_template(self, plan: str, path: str, limit: Any, universe_text: str) -> str:
        selected_plan = plan or "balanced"
        plan_labels = {value: label for label, value in RECOMMEND_PLAN_CHOICES}
        symbols = parse_stock_symbols(universe_text)
        universe = "、".join(symbols) if symbols else "市场热门领涨股自动池"
        count = max(1, min(int(limit or 10), 30))
        path_label = "深度分析" if path == "deep" else "快速分析"
        focus = {
            "defensive": "低波动、流动性、回撤约束",
            "momentum": "20 日动量、成交放大、趋势延续",
            "quality": "质量稳定、估值约束、盈利韧性",
            "event": "新闻强度、研报催化、产业主题",
            "chan": "缠论结构、门控信号、K 线位置",
            "balanced": "趋势、流动性、情绪和结构均衡",
        }.get(selected_plan, "综合评分")
        return (
            "### 推荐条件模板\n\n"
            f"- 方案：**{plan_labels.get(selected_plan, selected_plan)}**\n"
            f"- 分析路径：**{path_label}**；候选上限：**{count}**\n"
            f"- 股票池：{universe}\n"
            f"- 核心条件：{focus}\n"
            f"- 入池门槛：综合评分优先观察 `70+`，优势因子需能解释推荐理由。\n"
            f"- 验证动作：先对前 3-5 只候选运行同一策略回测，再看胜率、回撤、归因贡献和交易日志。\n"
            f"- 风险边界：推荐只给研究候选，不直接作为实盘指令；低流动性、单一情绪催化和结构分歧需要降权。"
        )

    def recommend_templates(self) -> pd.DataFrame:
        rows = Repository().list("recommend_templates", order_by="updated_at DESC", limit=50)
        for row in rows:
            row["updated_at"] = _format_display_time(row.get("updated_at"))
        return to_frame(rows, RECOMMEND_TEMPLATE_COLUMNS)

    def recommend_save_template(
        self, name: str, plan: str, path: str, limit: Any, universe_text: str
    ) -> tuple[str, pd.DataFrame]:
        repo = Repository()
        now = utc_now_iso()
        template_name = require_text(name, "模板名称")
        selected_plan = plan or "balanced"
        selected_path = path if path in {"quick", "deep"} else "quick"
        count = max(1, min(int(limit or 10), 30))
        payload = {
            "name": template_name,
            "plan": selected_plan,
            "path": selected_path,
            "limit_count": count,
            "universe_text": str(universe_text or "").strip(),
            "updated_at": now,
        }
        existing = repo.db.query_one("SELECT id FROM recommend_templates WHERE name = ?", (template_name,))
        if existing:
            repo.update("recommend_templates", int(existing["id"]), payload)
            action = "已更新"
        else:
            repo.insert("recommend_templates", {**payload, "created_at": now})
            action = "已保存"
        return f"推荐模板 `{template_name}` {action}。", self.recommend_templates()

    def recommend_load_template(self, template_id: Any) -> tuple[str, str, str, int, str]:
        row = Repository().get("recommend_templates", require_id(template_id, "模板 ID"))
        return (
            f"已加载推荐模板 `{row.get('name')}`。",
            str(row.get("plan") or "balanced"),
            str(row.get("path") or "quick"),
            int(row.get("limit_count") or 10),
            str(row.get("universe_text") or ""),
        )

    def recommend_group_compare(
        self,
        plans: Sequence[str] | None,
        path: str,
        limit: Any,
        universe_text: str,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame, go.Figure]:
        plan_labels = {value: label for label, value in RECOMMEND_PLAN_CHOICES}
        valid_plans = set(plan_labels)
        selected_plans: list[str] = []
        for plan in plans or []:
            value = str(plan or "").strip()
            if value in valid_plans and value not in selected_plans:
                selected_plans.append(value)
        if len(selected_plans) < 2:
            raise ValueError("请选择至少两个推荐方案进行横向对比")
        selected_plans = selected_plans[:6]
        selected_path = path if path in {"quick", "deep"} else "quick"
        path_label = "深度" if selected_path == "deep" else "快速"
        count = max(1, min(int(limit or 8), 30))
        symbols = parse_stock_symbols(universe_text)
        grouped_rows: dict[str, list[dict[str, Any]]] = {}
        task_ids: dict[str, int] = {}
        recommender = Recommender()
        for plan in selected_plans:
            payload: dict[str, Any] = {"path": selected_path, "plan": plan, "count": count}
            if symbols:
                payload["universe"] = {"symbols": symbols}
            task = recommender.create_task(payload)
            task_id = int(task["task_id"])
            task_ids[plan] = task_id
            grouped_rows[plan] = self._recommend_display_rows(recommender.result(task_id), plan)

        symbol_counts: dict[str, int] = {}
        for rows in grouped_rows.values():
            for row in rows:
                symbol = str(row.get("symbol") or "")
                if symbol:
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        summary_rows: list[dict[str, Any]] = []
        symbol_records: dict[str, dict[str, Any]] = {}
        score_matrix: dict[str, dict[str, float]] = {}
        for plan in selected_plans:
            rows = grouped_rows.get(plan, [])
            label = plan_labels.get(plan, plan)
            scores = [_safe_float(row.get("score")) for row in rows]
            group_symbols = [str(row.get("symbol") or "") for row in rows if row.get("symbol")]
            overlap_count = sum(1 for symbol in group_symbols if symbol_counts.get(symbol, 0) > 1)
            top = rows[0] if rows else {}
            summary_rows.append(
                {
                    "方案": label,
                    "路径": path_label,
                    "候选数": len(rows),
                    "平均评分": round(sum(scores) / len(scores), 2) if scores else 0.0,
                    "最高评分": round(max(scores), 2) if scores else 0.0,
                    "重合候选": overlap_count,
                    "独有候选": max(len(group_symbols) - overlap_count, 0),
                    "首位候选": f"{top.get('symbol', '-')}/{top.get('name', '-')}" if top else "-",
                    "任务ID": task_ids.get(plan, 0),
                }
            )
            for row in rows:
                symbol = str(row.get("symbol") or "")
                if not symbol:
                    continue
                name = str(row.get("name") or "-")
                score = _safe_float(row.get("score"))
                rank = int(_safe_float(row.get("rank"), 999))
                record = symbol_records.setdefault(
                    symbol,
                    {
                        "代码": symbol,
                        "名称": name,
                        "_plans": [],
                        "_scores": [],
                        "_best_score": score,
                        "_best_plan": label,
                        "_best_rank": rank,
                    },
                )
                record["_plans"].append(label)
                record["_scores"].append(score)
                if score > _safe_float(record.get("_best_score")):
                    record["_best_score"] = score
                    record["_best_plan"] = label
                    record["_best_rank"] = rank
                score_matrix.setdefault(symbol, {})[label] = score

        consensus_count = sum(1 for count_value in symbol_counts.values() if count_value > 1)
        symbol_rows = []
        for record in symbol_records.values():
            scores = list(record.get("_scores") or [])
            appear_count = len(scores)
            avg_score = round(sum(scores) / appear_count, 2) if scores else 0.0
            best_score = round(_safe_float(record.get("_best_score")), 2)
            if appear_count >= 2 and avg_score >= 75:
                action = "跨方案共识，优先验证"
            elif appear_count >= 2:
                action = "多方案观察，等待回测"
            else:
                action = "单方案候选，复核触发条件"
            symbol_rows.append(
                {
                    "代码": record.get("代码"),
                    "名称": record.get("名称"),
                    "出现组数": appear_count,
                    "覆盖方案": "、".join(str(item) for item in record.get("_plans") or []),
                    "平均评分": avg_score,
                    "最高评分": best_score,
                    "最佳方案": record.get("_best_plan"),
                    "最佳排名": int(_safe_float(record.get("_best_rank"), 999)),
                    "建议动作": action,
                }
            )
        symbol_rows.sort(
            key=lambda item: (
                -int(_safe_float(item.get("出现组数"))),
                -_safe_float(item.get("平均评分")),
                -_safe_float(item.get("最高评分")),
                int(_safe_float(item.get("最佳排名"), 999)),
            )
        )
        status = (
            f"已完成 {len(selected_plans)} 组推荐参数横向对比；"
            f"覆盖 {len(symbol_rows)} 只候选，跨方案共识 {consensus_count} 只。"
        )
        return (
            status,
            to_frame(summary_rows, RECOMMEND_GROUP_SUMMARY_COLUMNS),
            to_frame(symbol_rows, RECOMMEND_GROUP_SYMBOL_COLUMNS),
            recommend_group_compare_figure(summary_rows, symbol_rows, score_matrix),
        )

    def recommend_candidate_compare(
        self, recommend_rows: Any, fallback_symbols: str
    ) -> tuple[str, pd.DataFrame, go.Figure]:
        records = _recommend_records(recommend_rows)
        if not records:
            records = [
                {
                    "rank": index,
                    "symbol": symbol,
                    "name": symbol,
                    "score": 0.0,
                    "plan": "",
                    "reason": "来自手工股票池，尚未生成推荐评分",
                    "momentum": 0.0,
                    "liquidity": 0.0,
                    "sentiment": 0.0,
                    "chan": 0.0,
                }
                for index, symbol in enumerate(parse_stock_symbols(fallback_symbols), start=1)
            ]
        if not records:
            raise ValueError("推荐结果为空，请先生成推荐或输入股票池")
        rows: list[dict[str, Any]] = []
        for item in records[:10]:
            factor_scores = {
                RECOMMEND_FACTOR_LABELS[key]: _safe_float(item.get(key))
                for key in RECOMMEND_FACTOR_LABELS
                if key != "chan" or _safe_float(item.get(key)) > 0
            }
            best_factor = max(factor_scores.items(), key=lambda pair: pair[1])[0] if factor_scores else "综合评分"
            score = _safe_float(item.get("score"))
            liquidity = _safe_float(item.get("liquidity"))
            sentiment = _safe_float(item.get("sentiment"))
            risk = "常规波动风险，等待回测确认"
            if score and score < 70:
                risk = "评分未过 70，先观察不进入主验证池"
            elif liquidity and liquidity < 55:
                risk = "流动性偏弱，回测需降低成交假设"
            elif sentiment > 85:
                risk = "情绪拥挤，需防催化退潮"
            rows.append(
                {
                    "代码": item["symbol"],
                    "名称": item["name"],
                    "综合评分": round(score, 2),
                    "优势因子": best_factor,
                    "验证动作": "纳入推荐回测" if score >= 70 or not score else "先加入观察池",
                    "回测标的": "是" if len(rows) < 5 else "候补",
                    "风险提示": risk,
                }
            )
        return (
            f"已生成 {len(rows)} 个候选的对比视图，前 5 只可直接作为回测股票池。",
            to_frame(rows, RECOMMEND_COMPARE_COLUMNS),
            recommend_factor_figure(records),
        )

    def recommend_to_backtest(
        self,
        strategy_id: Any,
        recommend_rows: Any,
        fallback_symbols: str,
        start_date: str,
        end_date: str,
        capital: Any,
        params: str,
        engine: str,
    ) -> tuple[str, int, pd.DataFrame, go.Figure, pd.DataFrame, go.Figure, pd.DataFrame]:
        symbols = (parse_stock_symbols(recommend_rows) or parse_stock_symbols(fallback_symbols))[:5]
        if not symbols:
            raise ValueError("推荐结果为空，请先生成推荐或输入股票池")
        callbacks = cast(CrossDomainCallbacks, self)
        status, task_id, _, metrics, equity, trades, attribution_plot, attribution = callbacks.create_backtest(
            strategy_id,
            ",".join(symbols),
            start_date,
            end_date,
            capital,
            params,
            engine or "simple",
        )
        return (
            f"{status}；股票池来自推荐候选：{', '.join(symbols)}",
            task_id,
            metrics,
            equity,
            trades,
            attribution_plot,
            attribution,
        )

    def add_recommendations_to_watchlist(
        self,
        group_id: Any,
        recommend_rows: Any,
        fallback_symbols: str,
    ) -> tuple[str, pd.DataFrame, pd.DataFrame]:
        symbols = parse_stock_symbols(recommend_rows) or parse_stock_symbols(fallback_symbols)
        if not symbols:
            raise ValueError("推荐结果为空，请先生成推荐或输入股票池")
        service = QuoteService()
        value = self._ensure_watchlist_group(service, group_id)
        result = service.add_symbols(value, symbols[:30])
        added = result.get("added") or []
        return (
            f"推荐结果已加入自选分组 {value}：新增 {len(added)} 只，候选 {len(symbols[:30])} 只",
            self.watchlist_groups(),
            to_frame(service.watchlist_quotes(value), WATCHLIST_COLUMNS),
        )

    def recommend_first_to_relations(
        self,
        recommend_rows: Any,
        fallback_symbols: str,
        depth: Any,
        relation_types: Sequence[str] | None = None,
    ) -> tuple[str, str, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, go.Figure]:
        symbols = parse_stock_symbols(recommend_rows) or parse_stock_symbols(fallback_symbols)
        if not symbols:
            raise ValueError("推荐结果为空，请先生成推荐或输入股票池")
        selected_symbol = symbols[0]
        summary, analysis, paths, nodes, edges, figure = self.relations(selected_symbol, depth, relation_types)
        return (
            f"已同步首只候选 {selected_symbol} 到关系图谱",
            selected_symbol,
            summary,
            analysis,
            paths,
            nodes,
            edges,
            figure,
        )
