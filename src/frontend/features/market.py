"""Gradio UI for the market domain."""

from __future__ import annotations

import gradio as gr

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..common.navigation import workspace_link
from ..handlers import DomainHandler
from ..service.foundation import (
    BACKTEST_ENGINE_CHOICES,
    RECOMMEND_PLAN_CHOICES,
    RELATION_TYPE_CHOICES,
)


def render_market(service: DomainHandler, default_relation_types: list[str]) -> None:
    with gr.Tab("市场研究"):
        with gr.Tabs(elem_classes=["module-tabs"]):
            with gr.Tab("行情看盘"):
                with gr.Row():
                    market_board = gr.Dropdown(["industry", "concept"], value="industry", label="板块类型")
                    market_limit = gr.Slider(5, 100, value=20, step=5, label="展示数量")
                    market_refresh = gr.Button(
                        "刷新行情",
                        variant="primary",
                        scale=0,
                        min_width=120,
                        elem_classes=["page-refresh-btn"],
                    )
                market_indices = _table("指数行情", 280)
                with gr.Row():
                    market_sectors = _table("板块行情", 380)
                    market_plot = _plot(
                        label="板块涨跌",
                        elem_classes=["chart-panel"],
                    )
                market_refresh.click(
                    _safe(service.market_overview),
                    inputs=[market_board, market_limit],
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

            with gr.Tab("因子监控"):
                gr.Markdown("因子监控与研究使用统一的股票池、历史标签和诊断结果。")
                gr.HTML(workspace_link("打开因子研究与监控", "strategy", "factors"))

            with gr.Tab("新闻中心"):
                with gr.Row():
                    news_category = gr.Dropdown(
                        ["全部", "domestic", "international", "finance", "company"],
                        value="全部",
                        label="新闻分类",
                    )
                    news_keyword = gr.Textbox(label="关键词")
                    news_source = gr.Textbox(label="来源")
                    news_search = gr.Button("查询", variant="primary", elem_classes=["page-refresh-btn"])
                    news_refresh = gr.Button("同步最新")
                news_status = gr.Markdown(elem_classes=["compact-note"])
                news_table = _table("新闻列表", 430)
                with gr.Row():
                    news_detail_id = gr.Number(label="新闻 ID", precision=0)
                    news_detail_btn = gr.Button("查看详情")
                news_detail = gr.Markdown(label="新闻详情")
                news_cloud = _plot(
                    label="关键词强度",
                    elem_classes=["chart-panel"],
                )
                news_search.click(
                    _safe(
                        lambda category, keyword, source: service.news(category, keyword, source, force_refresh=True)
                    ),
                    inputs=[news_category, news_keyword, news_source],
                    outputs=[news_table, news_cloud, news_status],
                    queue=False,
                )
                news_refresh.click(
                    _safe(service.refresh_news),
                    inputs=[news_category, news_keyword, news_source],
                    outputs=[news_table, news_cloud, news_status],
                )
                news_detail_btn.click(_safe(service.news_detail), inputs=news_detail_id, outputs=news_detail)

            with gr.Tab("个股分析"):
                with gr.Row():
                    stock_symbol = gr.Textbox(value="600519", label="股票代码/名称")
                    stock_period = gr.Dropdown(["daily", "weekly", "monthly"], value="daily", label="K 线周期")
                    stock_count = gr.Slider(20, 240, value=60, step=20, label="K 线数量")
                    stock_query = gr.Button(
                        "分析",
                        variant="primary",
                        scale=0,
                        min_width=120,
                        elem_classes=["page-refresh-btn"],
                    )
                    stock_watch_group = gr.Number(label="自选分组 ID", precision=0)
                    stock_add_watch = gr.Button("加入自选")
                    stock_to_relation = gr.Button("同步关系图")
                stock_summary = gr.Markdown(elem_classes=["status-strip"])
                stock_watch_status = gr.Markdown(elem_classes=["status-strip"])
                stock_watchlist = _table("自选行情", 260)
                with gr.Row():
                    stock_score = _plot(
                        label="综合评分",
                        elem_classes=["chart-panel"],
                    )
                    stock_finance = _table("财务指标", 260)
                stock_kline = _plot(
                    label="K 线",
                    elem_classes=["chart-panel"],
                )
                with gr.Row():
                    stock_news = _table("相关资讯", 300)
                    stock_reports = _table("相关研报", 300)
                stock_query.click(
                    _safe(service.stock),
                    inputs=[stock_symbol, stock_period, stock_count],
                    outputs=[
                        stock_summary,
                        stock_score,
                        stock_finance,
                        stock_kline,
                        stock_news,
                        stock_reports,
                    ],
                    queue=False,
                )
                stock_add_watch.click(
                    _safe(service.add_stock_to_watchlist),
                    inputs=[stock_symbol, stock_watch_group],
                    outputs=[stock_watch_status, stock_watchlist],
                )

            with gr.Tab("关系图谱"):
                with gr.Row():
                    relation_symbol = gr.Textbox(value="600519", label="股票代码/名称")
                    relation_depth = gr.Slider(1, 5, value=3, step=1, label="关系深度（1-5层，越深越慢）")
                    relation_types = gr.CheckboxGroup(
                        choices=RELATION_TYPE_CHOICES,
                        value=default_relation_types,
                        label="关系类型",
                    )
                    relation_query = gr.Button(
                        "查询关系",
                        variant="primary",
                        scale=0,
                        min_width=120,
                        elem_classes=["page-refresh-btn"],
                    )
                    relation_export = gr.Button("导出图谱JSON")
                relation_summary = gr.Markdown(elem_classes=["status-strip"])
                relation_export_status = gr.Markdown(elem_classes=["status-strip"])
                relation_export_file = gr.Textbox(label="图谱导出文件路径", interactive=False)
                relation_plot = _plot(
                    label="关联网络",
                    elem_classes=["chart-panel"],
                )
                relation_fit = gr.Button("适应全部 / 重新居中")
                relation_evidence_choice = gr.Dropdown([], label="选择关系查看证据", interactive=True)
                relation_evidence = gr.HTML("<p>请选择关系查看来源、新闻内容及匹配依据。</p>")
                relation_plot.change(
                    _safe(service.relation_evidence_options),
                    inputs=relation_plot,
                    outputs=relation_evidence_choice,
                    queue=False,
                )
                relation_evidence_choice.change(
                    _safe(service.relation_evidence_detail),
                    inputs=[relation_plot, relation_evidence_choice],
                    outputs=relation_evidence,
                    queue=False,
                )
                relation_fit.click(
                    _safe(service.relation_fit), inputs=relation_plot, outputs=relation_plot, queue=False
                )
                relation_analysis = _table("图谱分析", 300)
                relation_paths = _table("层级链路", 300)
                with gr.Row():
                    relation_nodes = _table("节点", 400)
                    relation_edges = _table("关系", 400)
                relation_query.click(
                    _safe(service.relations),
                    inputs=[relation_symbol, relation_depth, relation_types],
                    outputs=[
                        relation_summary,
                        relation_analysis,
                        relation_paths,
                        relation_nodes,
                        relation_edges,
                        relation_plot,
                    ],
                    queue=False,
                )
                relation_export.click(
                    _safe(service.export_relations),
                    inputs=[relation_symbol, relation_depth, relation_types],
                    outputs=[relation_export_status, relation_export_file],
                    queue=False,
                )
                stock_to_relation.click(
                    _safe(service.stock_to_relations),
                    inputs=[stock_symbol, relation_depth, relation_types],
                    outputs=[
                        stock_watch_status,
                        relation_symbol,
                        relation_summary,
                        relation_analysis,
                        relation_paths,
                        relation_nodes,
                        relation_edges,
                        relation_plot,
                    ],
                    queue=False,
                )

            with gr.Tab("资源池"):
                pool_pipeline_activate = gr.Button("打开方案筛选", elem_id="workspace-activate-pool-pipeline")

                def _activate_pool_pipeline():
                    return gr.update(visible=False)

                pool_pipeline_activate.click(_activate_pool_pipeline, outputs=pool_pipeline_activate, queue=False)

                @gr.render(triggers=[pool_pipeline_activate.click], queue=False)
                def _render_pool_pipeline():
                    with gr.Accordion("组合方案级联筛选", open=False):
                        pool_pipeline = gr.Dropdown(service.pipeline_templates(), label="策略方案", interactive=True)
                        pool_backend = gr.Dropdown(
                            [("模型API", "api"), ("Codex CLI", "codex")],
                            value="api",
                            label="研究后端",
                            interactive=True,
                        )
                        pool_pipeline_run = gr.Button("按当前资源池筛选", variant="primary")
                        pool_snapshot = gr.Textbox(label="行情快照ID（留空重新采集）", interactive=True)
                        pool_pipeline_status = gr.Textbox(label="筛选状态", interactive=False)
                        pool_pipeline_process = gr.Textbox(label="实际筛选过程", lines=6, interactive=False)
                        pool_pipeline_report = gr.HTML()
                    pool_pipeline_run.click(
                        _safe(service.pipeline_pool_run),
                        inputs=[pool_pipeline, resource_pool_id, pool_backend, pool_snapshot],
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
                    resource_pool_id = gr.Number(label="资源池 ID（留空默认）", precision=0)
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
                    resource_import_partial = gr.Checkbox(
                        value=False, label="明确允许跳过错误行（跨市场等整文件错误仍阻断）"
                    )
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
                resource_pool_refresh.click(
                    _safe(service.resource_pools),
                    outputs=resource_pool_table,
                    queue=False,
                )
                resource_pool_create.click(
                    _safe(service.create_resource_pool),
                    inputs=[resource_pool_name, resource_pool_desc],
                    outputs=[resource_pool_status, resource_pool_table, resource_pool_items],
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
                security_lookup_button.click(
                    _safe(service.security_master_search),
                    inputs=[security_lookup_query, security_lookup_limit],
                    outputs=security_lookup_table,
                    queue=False,
                )
            with gr.Tab("股票推荐"):
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
                    recommend_to_relation = gr.Button("首只候选看关系")
                with gr.Row():
                    recommend_resource_pool_id = gr.Number(
                        label="资源池 ID（留空默认）",
                        precision=0,
                    )
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
                recommend_table = _table("推荐结果", 430)
                with gr.Accordion("推荐候选验证", open=True):
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
                    gr.Markdown("#### 推荐一键回测")
                    with gr.Row():
                        recommend_backtest_strategy_id = gr.Number(label="策略 ID", precision=0)
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
                        recommend_backtest_task_id = gr.Number(
                            label="回测任务 ID",
                            precision=0,
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
                recommend_to_relation.click(
                    _safe(service.recommend_first_to_relations),
                    inputs=[recommend_table, recommend_universe, relation_depth, relation_types],
                    outputs=[
                        recommend_status,
                        relation_symbol,
                        relation_summary,
                        relation_analysis,
                        relation_paths,
                        relation_nodes,
                        relation_edges,
                        relation_plot,
                    ],
                    queue=False,
                )
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
                recommend_backtest_run.click(
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
