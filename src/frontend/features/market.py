"""Gradio UI for the market domain."""

from __future__ import annotations

import gradio as gr
import pandas as pd

from src.agent.composer_config import cli_choices
from src.agent.providers.config import backend_names
from src.data import current_market
from src.engine.economics.config import economics_config
from src.engine.market.news_policy import news_policy
from src.strategy import StrategyStore

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..common.composer_catalog import bind_cli_catalog
from ..common.navigation import workspace_link
from ..handlers import DomainHandler
from ..service.foundation import (
    BACKTEST_ENGINE_CHOICES,
    INDEX_COLUMNS,
    RECOMMEND_PLAN_CHOICES,
    SECTOR_COLUMNS,
    parse_stock_symbols,
)
from .economics import render_economics
from .research_layout import research_panel, research_panels, research_tabs
from .stock_analysis import render_stock_analysis


def _render_quotes(service):
    with gr.Row():
        market_board = gr.Dropdown(["industry", "concept"], value="industry", label="板块类型")
        market_limit = gr.Slider(5, 100, value=20, step=5, label="展示数量")
        market_ranking = gr.Dropdown(
            [
                ("Gainers and decliners", "balanced"),
                ("Top gainers", "gainers"),
                ("Top decliners", "decliners"),
            ],
            value="balanced",
            label="Sector ranking",
        )
        market_refresh = gr.Button(
            "刷新规则数据",
            elem_id="market-quotes-refresh",
            variant="primary",
            scale=0,
            min_width=120,
            elem_classes=["page-refresh-btn", "route-control"],
        )
    gr.Markdown("点击刷新规则数据查看指数和板块。各区结果独立更新。", elem_classes=["compact-note"])
    market_indices = _table(
        "指数行情",
        280,
        elem_id="market-indices",
        elem_classes=["home-semantic-table"],
        value=pd.DataFrame(columns=INDEX_COLUMNS),
        compact=True,
    )
    with gr.Row():
        market_sectors = _table(
            "板块行情",
            380,
            elem_id="market-sectors",
            elem_classes=["home-semantic-table"],
            value=pd.DataFrame(columns=["ranking", *SECTOR_COLUMNS]),
            compact=True,
        )
        market_plot = _plot(
            label="板块涨跌",
            elem_id="market-sectors-plot",
            elem_classes=["chart-panel"],
        )
    market_refresh.click(
        _safe(service.market_overview),
        inputs=[market_board, market_limit, market_ranking],
        outputs=[market_indices, market_sectors, market_plot],
        queue=False,
    )
    with gr.Accordion("自选管理", open=False):
        market_watch_status = gr.Markdown(elem_classes=["status-strip"])
        with gr.Row():
            watch_group_name = gr.Textbox(label="分组名称")
            watch_group_order = gr.Number(value=0, label="排序", precision=0)
            watch_group_create = gr.Button("新建分组", variant="primary")
            watch_group_refresh = gr.Button("刷新分组")
        watch_groups = _table("自选分组", 260)
        with gr.Row():
            watch_group_id = gr.Number(label="分组 ID", precision=0)
            watch_symbols = gr.Textbox(
                label="股票代码/名称",
                placeholder="600519, 贵州茅台, 宁德时代, AAPL",
            )
            watch_add = gr.Button("加入自选", variant="primary")
            watch_remove_symbol = gr.Textbox(label="删除代码")
            watch_remove = gr.Button("删除标的", variant="stop")
        watch_quotes = _table("分组行情", 320)
        watch_group_refresh.click(_safe(service.watchlist_groups), outputs=watch_groups)
        watch_group_create.click(
            _safe(service.create_watchlist_group),
            inputs=[watch_group_name, watch_group_order],
            outputs=[market_watch_status, watch_groups],
        )
        watch_add.click(
            _safe(service.add_watchlist_symbols),
            inputs=[watch_group_id, watch_symbols],
            outputs=[market_watch_status, watch_groups, watch_quotes],
        )
        watch_remove.click(
            _safe(service.remove_watchlist_symbol),
            inputs=[watch_group_id, watch_remove_symbol],
            outputs=[market_watch_status, watch_groups, watch_quotes],
        )
    return watch_groups, watch_quotes


def _render_news(service):
    gr.Markdown(
        "Market and policy relevant news · geography and topic are independent; inclusion is not a price forecast."
    )
    with gr.Row():
        news_category = gr.Dropdown(
            ["全部", "domestic", "international", "finance", "company"],
            value="全部",
            label="新闻分类",
            visible=False,
            elem_id="news-category",
        )
        news_region = gr.Dropdown(news_policy()["ui"]["regions"], value="all", label="新闻地区", elem_id="news-region")
        news_topic = gr.Dropdown(news_policy()["ui"]["topics"], value="all", label="新闻主题", elem_id="news-topic")
        news_keyword = gr.Textbox(label="关键词", elem_id="news-keyword")
        news_source = gr.Textbox(label="来源", elem_id="news-source")
        news_search = gr.Button(
            "查询",
            variant="primary",
            elem_classes=["page-refresh-btn"],
            elem_id="market-news-query",
        )
        news_refresh = gr.Button("同步最新")
    news_status = gr.Markdown("设置筛选条件后查询新闻。", elem_classes=["compact-note"])
    news_table = _table(
        "新闻列表",
        360,
        elem_id="market-news-results",
        compact=True,
        value=pd.DataFrame(columns=["title", "source", "published_at", "region", "topics", "id"]),
    )
    news_detail = gr.HTML(elem_id="market-news-detail")
    news_cloud = _plot(
        label="关键词强度",
        elem_classes=["chart-panel"],
    )
    news_search.click(
        _safe(
            lambda category, keyword, source, region, topic: service.news(
                category, keyword, source, force_refresh=True, region=region, topic=topic
            ),
            section_styles=False,
        ),
        inputs=[news_category, news_keyword, news_source, news_region, news_topic],
        outputs=[news_table, news_cloud, news_status],
        queue=False,
    )
    news_refresh.click(
        _safe(service.refresh_news, section_styles=False),
        inputs=[news_category, news_keyword, news_source, news_region, news_topic],
        outputs=[news_table, news_cloud, news_status],
    )

    def selected_story(rows, event: gr.SelectData):
        if not event.selected or not isinstance(event.index, (list, tuple)):
            return ""
        index = event.index[0]
        if "id" not in rows or not 0 <= index < len(rows):
            return ""
        return service.news_detail(rows.iloc[index]["id"])

    news_table.select(_safe(selected_story), inputs=news_table, outputs=news_detail, queue=False)
    news_table.change(lambda: "", outputs=news_detail, queue=False)


def _render_resources(service):
    pool_pipeline_activate = gr.Button("打开方案筛选", elem_id="workspace-activate-pool-pipeline")

    def _activate_pool_pipeline():
        return gr.update(visible=False)

    pool_pipeline_activate.click(_activate_pool_pipeline, outputs=pool_pipeline_activate, queue=False)

    @gr.render(triggers=[pool_pipeline_activate.click], queue=False)
    def _render_pool_pipeline():
        with gr.Accordion("组合方案级联筛选", open=False):
            pool_pipeline = gr.Dropdown(service.pipeline_templates(), label="策略方案", interactive=True)
            pool_backend = gr.Dropdown(
                cli_choices(backend_names(), api="api"),
                value="api",
                label="研究后端",
                interactive=True,
            )
            with gr.Row():
                pool_model = gr.Dropdown([], label="CLI 模型", interactive=False)
                refresh_models = gr.Button("刷新模型", scale=0)
            catalog_note = gr.Markdown()
            bind_cli_catalog(pool_backend, pool_model, refresh_models, catalog_note, "api")
            pool_pipeline_run = gr.Button("按当前资源池筛选", variant="primary")
            pool_snapshot = gr.Textbox(label="行情快照ID（留空重新采集）", interactive=True)
            pool_pipeline_status = gr.Textbox(label="筛选状态", interactive=False)
            pool_pipeline_process = gr.Textbox(label="实际筛选过程", lines=6, interactive=False)
            pool_pipeline_report = gr.HTML()
        pool_pipeline_run.click(
            _safe(service.pipeline_pool_run),
            inputs=[pool_pipeline, resource_pool_id, pool_backend, pool_snapshot, pool_model],
            outputs=[pool_pipeline_status, pool_pipeline_process, pool_pipeline_report],
        )

    resource_pool_status = gr.Markdown(elem_classes=["status-strip"])
    with gr.Row():
        resource_pool_name = gr.Textbox(
            value="核心观察池",
            label="资源池名称",
            scale=2,
        )
        resource_pool_desc = gr.Textbox(
            label="说明",
            placeholder="例如：AI 推荐候选、行业主题、回测候选",
            scale=3,
        )
        resource_pool_create = gr.Button("保存资源池", variant="primary")
        resource_pool_refresh = gr.Button("刷新", elem_classes=["page-refresh-btn"])
    resource_pool_table = _table("资源池列表", 260)
    with gr.Row():
        resource_pool_id = gr.Dropdown(label="资源池", elem_id="market-resource-pool", choices=[], interactive=True)
        resource_pool_symbols = gr.Textbox(
            label="手工输入标的",
            placeholder="600519, 贵州茅台, 宁德时代, AAPL, 英伟达",
            scale=3,
        )
        resource_pool_weight = gr.Number(value=1.0, label="权重")
        resource_pool_remark = gr.Textbox(label="备注", scale=2)
        resource_pool_add = gr.Button("加入资源池", variant="primary")
    with gr.Row():
        resource_pool_file = gr.File(
            label="CSV / Excel 导入",
            elem_id="resource-pool-upload",
            file_count="single",
            file_types=[".csv", ".xlsx"],
            scale=3,
        )
        resource_pool_validate = gr.Button("校验并预览", variant="primary")
        resource_pool_import = gr.Button("确认导入")
        resource_pool_view = gr.Button("查看标的")
    with gr.Row():
        gr.DownloadButton("下载CSV模板", value=service.resource_template("csv"))
        gr.DownloadButton("下载Excel模板", value=service.resource_template("xlsx"))
        resource_import_mode = gr.Dropdown(
            [("更新已有标的", "merge"), ("跳过已有标的", "skip")], value="merge", label="冲突处理"
        )
        resource_import_partial = gr.Checkbox(value=False, label="明确允许跳过错误行（跨市场等整文件错误仍阻断）")
    gr.Markdown(
        "字段：market、symbol、name、weight、tags、remark。证券代码为文本；weight是候选评分权重，不要求合计为1。旧XLS请转换为XLSX。"
    )
    resource_import_state = gr.State({})
    with gr.Accordion("导入预览与逐行错误", open=True):
        resource_import_preview = _table("新增、更新与跳过预览")
        resource_import_errors = _table("错误行与修正建议")
        resource_import_error_file = gr.File(label="下载错误报告", interactive=False)
    resource_pool_items = _table("资源池标的", 360)
    with gr.Row():
        security_lookup_query = gr.Textbox(
            label="证券主数据搜索",
            placeholder="输入代码、名称、拼音或别名，例如 茅台 / ningde / NVDA",
            scale=4,
        )
        security_lookup_limit = gr.Number(value=20, label="返回数量", precision=0)
        security_lookup_button = gr.Button("搜索证券", variant="primary")
    security_lookup_table = _table("证券主数据匹配", 260)

    def refresh_pools(selected):
        table = service.resource_pools()
        return table, _pool_choices(table, selected)

    def create_pool(name, description):
        status, table, items = service.create_resource_pool(name, description)
        selected = table.loc[table["name"] == name.strip(), "id"].iloc[0]
        return status, table, items, _pool_choices(table, selected)

    resource_pool_refresh.click(
        _safe(refresh_pools),
        inputs=resource_pool_id,
        outputs=[resource_pool_table, resource_pool_id],
        queue=False,
    )
    resource_pool_create.click(
        _safe(create_pool),
        inputs=[resource_pool_name, resource_pool_desc],
        outputs=[resource_pool_status, resource_pool_table, resource_pool_items, resource_pool_id],
    )
    resource_pool_add.click(
        _safe(service.add_resource_pool_symbols),
        inputs=[
            resource_pool_id,
            resource_pool_symbols,
            resource_pool_remark,
            resource_pool_weight,
        ],
        outputs=[resource_pool_status, resource_pool_table, resource_pool_items],
    )
    resource_pool_validate.click(
        _safe(service.resource_import_preview),
        inputs=[resource_pool_id, resource_pool_file, resource_import_mode],
        outputs=[
            resource_pool_status,
            resource_import_preview,
            resource_import_errors,
            resource_import_error_file,
            resource_import_state,
        ],
    )
    resource_pool_import.click(
        _safe(service.resource_import_commit),
        inputs=[
            resource_pool_id,
            resource_pool_file,
            resource_import_mode,
            resource_import_partial,
            resource_import_state,
        ],
        outputs=[resource_pool_status, resource_pool_table, resource_pool_items],
    )
    resource_pool_view.click(
        _safe(service.resource_pool_items),
        inputs=resource_pool_id,
        outputs=resource_pool_items,
        queue=False,
    )
    resource_pool_id.input(
        _safe(service.resource_pool_items), inputs=resource_pool_id, outputs=resource_pool_items, queue=False
    )
    security_lookup_button.click(
        _safe(service.security_master_search),
        inputs=[security_lookup_query, security_lookup_limit],
        outputs=security_lookup_table,
        queue=False,
    )
    return resource_pool_table, resource_pool_items


def _pool_choices(table, selected=None):
    choices = [(str(row.name), int(row.id)) for row in table.itertuples(index=False)]
    return gr.update(choices=choices, value=int(selected) if selected in {key for _, key in choices} else None)


def _render_recommendations(service, watch_groups, watch_quotes, resource_pool_table, resource_pool_items):
    with gr.Tabs(elem_id="recommendation-workspace"):
        with gr.Tab("推荐", id="recommendation"):
            with gr.Row():
                recommend_plan = gr.Dropdown(RECOMMEND_PLAN_CHOICES, value="balanced", label="推荐方案")
                recommend_path = gr.Radio(
                    choices=[("快速", "quick"), ("深度", "deep")],
                    value="quick",
                    label="分析路径",
                )
                recommend_limit = gr.Slider(5, 30, value=10, step=1, label="推荐数量")
                recommend_universe = gr.Textbox(
                    label="股票池（逗号分隔，留空取市场热门领涨股）",
                    placeholder="如：600519,300750,688981",
                    scale=2,
                )
            recommend_run = gr.Button("生成推荐", variant="primary", elem_classes=["page-refresh-btn"])
            with gr.Row():
                recommend_watch_group = gr.Number(
                    label="加入自选分组 ID（留空默认）",
                    precision=0,
                )
                recommend_add_watch = gr.Button("批量加入自选", variant="primary")
                recommend_stock_link = gr.HTML(elem_id="recommend-stock-link")
            with gr.Row():
                recommend_resource_pool_id = gr.Dropdown(
                    label="筛选资源池", choices=[], interactive=True, elem_id="screening-resource-pool"
                )
                refresh_pool_choices = gr.Button("刷新资源池选项")
                recommend_add_resource = gr.Button("批量加入资源池", variant="primary")
                recommend_load_resource = gr.Button("载入资源池到股票池")
            recommend_status = gr.Markdown(elem_classes=["status-strip"])
            with gr.Accordion("推荐模板库", open=False):
                with gr.Row():
                    recommend_template_name = gr.Textbox(
                        label="模板名称",
                        value="默认推荐模板",
                        scale=2,
                    )
                    recommend_template_save = gr.Button("保存推荐模板", variant="primary")
                    recommend_template_refresh = gr.Button("刷新模板")
                with gr.Row():
                    recommend_template_id = gr.Number(label="模板 ID", precision=0)
                    recommend_template_load = gr.Button("加载模板")
                recommend_templates = _table("推荐模板库", 240)
            recommend_table = _table("推荐结果", 430, elem_id="market-recommendation-results")
        with gr.Tab("候选对比", id="candidate-comparison"):
            with gr.Row():
                recommend_template_btn = gr.Button("生成条件模板")
                recommend_compare_btn = gr.Button("候选对比", variant="primary")
            recommend_template = gr.Markdown(elem_classes=["compact-note"])
            recommend_compare_plot = _plot(
                label="因子对比",
                elem_classes=["chart-panel"],
            )
            recommend_compare_table = _table("候选对比", 280)
            gr.Markdown("#### 多组参数横向对比")
            with gr.Row():
                recommend_group_plans = gr.CheckboxGroup(
                    RECOMMEND_PLAN_CHOICES,
                    value=["balanced", "momentum", "quality"],
                    label="对比方案",
                    scale=2,
                )
                recommend_group_path = gr.Radio(
                    choices=[("快速", "quick"), ("深度", "deep")],
                    value="quick",
                    label="对比路径",
                )
                recommend_group_limit = gr.Slider(
                    3,
                    20,
                    value=8,
                    step=1,
                    label="每组数量",
                )
            recommend_group_compare_btn = gr.Button("多组参数对比", variant="primary")
            recommend_group_status = gr.Markdown(elem_classes=["status-strip"])
            recommend_group_plot = _plot(
                label="多组对比图",
                elem_classes=["chart-panel"],
            )
            with gr.Row():
                recommend_group_summary = _table("方案对比摘要", 260)
                recommend_group_symbols = _table("共识候选", 260)
        with gr.Tab("回测", id="recommendation-backtest") as backtest_section:
            with gr.Row():
                recommend_backtest_strategy_id = gr.Dropdown(
                    label="回测策略", choices=[], interactive=True, elem_id="screening-backtest-strategy"
                )
                refresh_strategy_choices = gr.Button("刷新策略选项")
                recommend_backtest_engine = gr.Dropdown(
                    BACKTEST_ENGINE_CHOICES,
                    value="simple",
                    label="回测引擎",
                )
                recommend_backtest_capital = gr.Number(value=1000000, label="初始资金")
            with gr.Row():
                recommend_backtest_start = gr.Textbox(value="2026-01-01", label="开始日期")
                recommend_backtest_end = gr.Textbox(value="2026-06-30", label="结束日期")
                recommend_backtest_params = gr.Code(
                    value="{}",
                    language="json",
                    label="策略参数",
                )
            recommend_backtest_run = gr.Button("用前 5 只候选创建回测", variant="primary")
            with gr.Row():
                recommend_backtest_status = gr.Markdown(elem_classes=["status-strip"])
                recommend_backtest_task_id = gr.Textbox(
                    value="",
                    label="回测任务 ID",
                    interactive=False,
                )
            with gr.Tabs():
                with gr.Tab("绩效"):
                    recommend_backtest_metrics = _table("推荐回测绩效", 240)
                    recommend_backtest_plot = _plot(
                        label="净值曲线",
                        elem_classes=["chart-panel"],
                    )
                with gr.Tab("归因"):
                    recommend_backtest_attribution_plot = _plot(
                        label="归因摘要",
                        elem_classes=["chart-panel"],
                    )
                    recommend_backtest_attribution = _table("推荐回测归因明细", 240)
                with gr.Tab("交易"):
                    recommend_backtest_trades = _table("推荐回测交易明细", 260)
    recommend_run.click(
        _safe(service.recommend),
        inputs=[recommend_plan, recommend_path, recommend_limit, recommend_universe],
        outputs=[recommend_status, recommend_table],
        queue=False,
    )
    recommend_add_watch.click(
        _safe(service.add_recommendations_to_watchlist),
        inputs=[recommend_watch_group, recommend_table, recommend_universe],
        outputs=[recommend_status, watch_groups, watch_quotes],
    )
    recommend_add_resource.click(
        _safe(service.add_recommendations_to_resource_pool),
        inputs=[recommend_resource_pool_id, recommend_table, recommend_universe],
        outputs=[recommend_status, resource_pool_table, resource_pool_items],
    )
    recommend_load_resource.click(
        _safe(service.resource_pool_to_universe),
        inputs=recommend_resource_pool_id,
        outputs=[recommend_status, recommend_universe, resource_pool_items],
        queue=False,
    )
    refresh_pool_choices.click(
        _safe(lambda selected: _pool_choices(service.resource_pools(), selected)),
        inputs=recommend_resource_pool_id,
        outputs=recommend_resource_pool_id,
        queue=False,
    )
    resource_pool_table.change(
        _pool_choices,
        inputs=[resource_pool_table, recommend_resource_pool_id],
        outputs=recommend_resource_pool_id,
        queue=False,
    )

    def backtest_strategy_choices(selected):
        strategies = StrategyStore().list(page_size=500)["items"]
        choices = [(f"{row['name']} · {row['version']}", row["id"]) for row in strategies if row["status"] != "停用"]
        return gr.update(choices=choices, value=selected if selected in {key for _, key in choices} else None)

    for activate in (backtest_section.select, refresh_strategy_choices.click):
        activate(
            _safe(backtest_strategy_choices),
            inputs=recommend_backtest_strategy_id,
            outputs=recommend_backtest_strategy_id,
            queue=False,
        )

    def open_candidate(rows, event: gr.SelectData):
        if not event.selected or not isinstance(event.index, (list, tuple)):
            return ""
        index = event.index[0]
        if not 0 <= index < len(rows):
            return ""
        symbols = parse_stock_symbols(rows.iloc[[index]])
        if not symbols:
            return ""
        return workspace_link("查看所选股票", "market", "stock", symbol=symbols[0], market=current_market().lower())

    recommend_table.select(_safe(open_candidate), inputs=recommend_table, outputs=recommend_stock_link, queue=False)
    recommend_table.change(lambda: "", outputs=recommend_stock_link, queue=False)
    recommend_template_save.click(
        _safe(service.recommend_save_template),
        inputs=[
            recommend_template_name,
            recommend_plan,
            recommend_path,
            recommend_limit,
            recommend_universe,
        ],
        outputs=[recommend_status, recommend_templates],
    )
    recommend_template_refresh.click(
        _safe(service.recommend_templates),
        outputs=recommend_templates,
        queue=False,
    )
    recommend_template_load.click(
        _safe(service.recommend_load_template),
        inputs=recommend_template_id,
        outputs=[
            recommend_status,
            recommend_plan,
            recommend_path,
            recommend_limit,
            recommend_universe,
        ],
        queue=False,
    )
    recommend_template_btn.click(
        _safe(service.recommend_condition_template),
        inputs=[recommend_plan, recommend_path, recommend_limit, recommend_universe],
        outputs=recommend_template,
        queue=False,
    )
    recommend_compare_btn.click(
        _safe(service.recommend_candidate_compare),
        inputs=[recommend_table, recommend_universe],
        outputs=[recommend_status, recommend_compare_table, recommend_compare_plot],
        queue=False,
    )
    recommend_group_compare_btn.click(
        _safe(service.recommend_group_compare),
        inputs=[
            recommend_group_plans,
            recommend_group_path,
            recommend_group_limit,
            recommend_universe,
        ],
        outputs=[
            recommend_group_status,
            recommend_group_summary,
            recommend_group_symbols,
            recommend_group_plot,
        ],
        queue=False,
    )
    pending = recommend_backtest_run.click(
        lambda: ("正在提交回测…", ""),
        outputs=[recommend_backtest_status, recommend_backtest_task_id],
        queue=False,
    )
    pending.then(
        _safe(service.recommend_to_backtest),
        inputs=[
            recommend_backtest_strategy_id,
            recommend_table,
            recommend_universe,
            recommend_backtest_start,
            recommend_backtest_end,
            recommend_backtest_capital,
            recommend_backtest_params,
            recommend_backtest_engine,
        ],
        outputs=[
            recommend_backtest_status,
            recommend_backtest_task_id,
            recommend_backtest_metrics,
            recommend_backtest_plot,
            recommend_backtest_trades,
            recommend_backtest_attribution_plot,
            recommend_backtest_attribution,
        ],
    )


def render_market(service: DomainHandler, default_relation_types: list[str]) -> None:
    with gr.Tab("市场研究"):
        gr.HTML(
            '<div class="research-actions" hidden>'
            '<button type="button" data-research-refresh hidden>刷新规则数据</button>'
            '<button type="button" class="page-report-action" hidden>AI 分析</button>'
            "</div>",
            elem_id="research-workspace-actions",
        )
        gr.HTML(
            '<nav class="research-standalone-nav" aria-label="市场研究">'
            '<a href="?view=analysis">市场分析</a>'
            '<a href="?view=stock">个股分析</a>'
            "</nav>",
        )
        with gr.Column(elem_id="market-research-views"):
            with gr.Column(elem_id="market-analysis-view", elem_classes=["research-page"]):
                research_tabs("analysis")
                with research_panels("analysis"):
                    with research_panel("quotes"):
                        watch_groups, watch_quotes = _render_quotes(service)
                    with research_panel("macro"):
                        render_economics(service, "macro", show_report=False)
                    with research_panel("news"):
                        _render_news(service)
                    with research_panel("resources"):
                        resource_pool_table, resource_pool_items = _render_resources(service)
                    with research_panel("recommendations"):
                        _render_recommendations(
                            service, watch_groups, watch_quotes, resource_pool_table, resource_pool_items
                        )
            with gr.Column(elem_id="market-stock-view", elem_classes=["research-page"]):
                stock_symbol = gr.Textbox(
                    value=economics_config()["defaults"]["company_symbols"].get(current_market(), ""),
                    label="股票代码/名称",
                    elem_id="fundamentals-symbol",
                )
                render_stock_analysis(service, default_relation_types, stock_symbol)
