"""Single-security research tabs and page-owned graph construction."""

from html import escape

import gradio as gr

from src.core.diagnostics_config import diagnostics_config
from src.core.page_work import CURRENT_PAGE
from src.engine.market.model_graph.config import config as model_graph_config
from src.frontend.service.rule_graph_view import rule_graph_view

from ..common.callbacks import safe as _safe
from ..common.components import plot as _plot
from ..common.components import table as _table
from ..handlers import DomainHandler
from ..service.foundation import RELATION_TYPE_CHOICES
from .economics import render_economics
from .model_relation_graph import render_model_graph_panel


def render_stock_analysis(service: DomainHandler, default_relation_types: list[str], stock_symbol: gr.Textbox) -> None:
    security_title = gr.Markdown(elem_id="stock-analysis-security")

    def load_profile(symbol):
        values = service.stock_profile(symbol)
        details = dict(zip(values["指标"], values["数值"], strict=True))
        code = details["证券代码"]
        return values, escape(f"{details['公司名称'] or code} · {code}")

    def rule_jobs():
        from src.engine.market.rule_graph_jobs import RuleGraphJobs

        return RuleGraphJobs()

    def enqueue_rules(symbol, depth, types):
        row = rule_jobs().start(symbol, depth, types)
        return row["run_id"], f"{row['run_id']} · {row['status']}", gr.update(active=True)

    def poll_rules(key):
        page = CURRENT_PAGE.get()
        if (
            not key
            or page
            and page.view_label
            and page.view_label not in {("market", "stock/relationships"), ("market", "relations")}
        ):
            return *(gr.skip() for _ in range(6)), gr.update(active=False)
        jobs = rule_jobs()
        row = jobs.detail(key)
        if row["status"] in {"completed", "partial"}:
            return *rule_graph_view(jobs.store.result(key)), gr.update(active=False)
        if row["status"] in {"cancelled", "failed", "interrupted"}:
            return (f"{key} · {row['status']} · {row.get('reason', '')}", [], [], [], [], None, gr.update(active=False))
        return (
            f"{key} · {row['status']} · {row.get('stage', 'Waiting for source')} · {row.get('reason', '')}",
            *(gr.skip() for _ in range(5)),
            gr.update(active=row["status"] in {"queued", "running"}),
        )

    with gr.Tabs(elem_id="stock-research-tabs", selected="fundamentals"):
        with gr.Tab("基本面", id="fundamentals"):
            read_profile = gr.Button("读取上市公司概况", variant="primary", elem_id="stock-profile-load")
            profile = _table("上市公司概况", 340)
            read_profile.click(_safe(load_profile), inputs=stock_symbol, outputs=[profile, security_title])
        with gr.Tab("Technical analysis", id="technical"):
            stock_period = gr.Dropdown(["daily", "weekly", "monthly"], value="daily", label="K 线周期")
            stock_count = gr.Slider(20, 240, value=80, step=20, label="K 线数量")
            stock_query = gr.Button(
                "分析",
                variant="primary",
                scale=0,
                min_width=120,
                elem_classes=["page-refresh-btn"],
                elem_id="stock-technical-load",
            )
            stock_watch_group = gr.Number(label="自选分组 ID", precision=0)
            stock_add_watch = gr.Button("加入自选")
            stock_summary = gr.Markdown(elem_classes=["status-strip"])
            stock_watch_status = gr.Markdown(elem_classes=["status-strip"])
            stock_watchlist = _table("自选行情", 260)
            with gr.Row():
                stock_score = _plot(
                    label="综合评分",
                    elem_classes=["chart-panel"],
                )
                stock_finance = _table("技术指标解读", 320, elem_id="stock-indicator-readings")
            stock_kline = _plot(
                label="K 线",
                elem_id="stock-kline-chart",
                elem_classes=["chart-panel", "no-i18n"],
            )
            stock_add_watch.click(
                _safe(service.add_stock_to_watchlist),
                inputs=[stock_symbol, stock_watch_group],
                outputs=[stock_watch_status, stock_watchlist],
            )

        with gr.Tab("Financial analysis", id="financials"):
            render_economics(service, "fundamentals", shared_symbol=stock_symbol)
        with gr.Tab("新闻与公告", id="disclosures"):
            stock_news_status = gr.Markdown()
            stock_news_query = gr.Button("读取公司资讯", variant="primary", elem_id="stock-news-load")
            stock_news = _table("相关资讯", 300)
            stock_reports = _table("相关研报", 300)
            stock_news_query.click(
                _safe(service.stock_disclosures),
                inputs=stock_symbol,
                outputs=[stock_news_status, stock_news, stock_reports],
            )
        with gr.Tab("关系图谱", id="relationships"):
            saved_relations = gr.Button("查看该标的已保存的关系")
            saved_relation_rows = _table("最近保存的关系", 300)
            saved_relations.click(_safe(service.stock_relationships), inputs=stock_symbol, outputs=saved_relation_rows)
            relation_mode = gr.Radio(
                model_graph_config()["ui"]["modes"],
                value="rules",
                label="Graph construction mode",
                elem_id="relation-graph-mode",
            )
            with gr.Group(visible=True) as rule_graph_panel:
                with gr.Row():
                    relation_depth = gr.Slider(
                        1,
                        5,
                        value=diagnostics_config()["rules"]["default_depth"],
                        step=1,
                        label="关系深度（1-5层，越深越慢）",
                    )
                    relation_types = gr.CheckboxGroup(
                        choices=RELATION_TYPE_CHOICES,
                        value=default_relation_types,
                        label="关系类型",
                    )
                    relation_query = gr.Button(
                        "查询关系",
                        elem_id="rule-graph-start",
                        variant="primary",
                        scale=0,
                        min_width=120,
                        elem_classes=["page-refresh-btn"],
                    )
                    relation_export = gr.Button("导出图谱JSON")
                relation_summary = gr.Markdown(elem_classes=["status-strip"], elem_id="rule-graph-status")
                relation_export_status = gr.Markdown(elem_classes=["status-strip"])
                relation_export_file = gr.Textbox(label="图谱导出文件路径", interactive=False)
                rule_run_id = gr.Textbox(label="Rule graph run ID", elem_id="rule-graph-run-id", interactive=False)
                rule_timer = gr.Timer(value=1, active=False)
                rule_cancel = gr.Button("Cancel rule graph", elem_id="rule-graph-cancel")
                rule_download = gr.File(label="Saved rule graph export", elem_id="rule-graph-download")
                relation_plot = _plot(
                    label="关联网络",
                    elem_id="rule-graph-plot",
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
                rule_run_id.change(
                    lambda: ([], [], [], [], None, "", "", None),
                    outputs=[
                        relation_analysis,
                        relation_paths,
                        relation_nodes,
                        relation_edges,
                        relation_plot,
                        relation_export_status,
                        relation_export_file,
                        rule_download,
                    ],
                    queue=False,
                )
                relation_query.click(
                    _safe(enqueue_rules),
                    inputs=[stock_symbol, relation_depth, relation_types],
                    outputs=[
                        rule_run_id,
                        relation_summary,
                        rule_timer,
                    ],
                    queue=False,
                )
                relation_export.click(
                    _safe(
                        lambda key: (
                            rule_jobs().store.result(key) and "Saved graph exported",
                            str(rule_jobs().store.directory(key) / "graph.json"),
                            str(rule_jobs().store.directory(key) / "graph.json"),
                        )
                    ),
                    inputs=rule_run_id,
                    outputs=[relation_export_status, relation_export_file, rule_download],
                    queue=True,
                )
                rule_cancel.click(
                    _safe(lambda key: rule_jobs().store.cancel(key)["status"]),
                    inputs=rule_run_id,
                    outputs=relation_summary,
                    queue=False,
                )
                rule_timer.tick(
                    _safe(poll_rules),
                    inputs=rule_run_id,
                    outputs=[
                        relation_summary,
                        relation_analysis,
                        relation_paths,
                        relation_nodes,
                        relation_edges,
                        relation_plot,
                        rule_timer,
                    ],
                    queue=False,
                )
            relation_mode.change(
                lambda mode: gr.update(visible=mode == "rules"),
                inputs=relation_mode,
                outputs=rule_graph_panel,
                queue=False,
            )

            stock_symbol.change(
                lambda: ("", "", gr.update(active=False)),
                outputs=[rule_run_id, relation_summary, rule_timer],
                queue=False,
            )

            @gr.render(inputs=relation_mode, triggers=[relation_mode.change], queue=False)
            def _render_selected_relation_mode(mode):
                if mode == "model":
                    render_model_graph_panel(stock_symbol)

        with gr.Tab("事件与风险", id="events-risk"):
            risk_query = gr.Button("计算风险指标", variant="primary", elem_id="stock-risk-load")
            stock_risk = _table("风险指标", 260)
            risk_query.click(_safe(service.stock_risk), inputs=stock_symbol, outputs=stock_risk)
            event_query = gr.Button("读取历史财报公告日期")
            event_status = gr.Markdown()
            stock_events = _table("历史财报公告日期", 300)
            event_query.click(_safe(service.stock_events), inputs=stock_symbol, outputs=[event_status, stock_events])
    stock_query.click(
        _safe(service.stock),
        inputs=[stock_symbol, stock_period, stock_count],
        outputs=[stock_summary, stock_score, stock_finance, stock_kline, stock_news, stock_reports],
        queue=False,
    )
    stock_symbol.change(
        lambda: ("", None, [], None, "", [], [], [], [], [], "", [], ""),
        outputs=[
            stock_summary,
            stock_score,
            stock_finance,
            stock_kline,
            stock_news_status,
            stock_news,
            stock_reports,
            profile,
            saved_relation_rows,
            stock_risk,
            event_status,
            stock_events,
            security_title,
        ],
        queue=False,
    )
