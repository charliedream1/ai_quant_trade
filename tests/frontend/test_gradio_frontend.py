import asyncio
import importlib.util
import inspect
import json
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urljoin

import pytest

import gradio as gr
from src.frontend.mounting import LazyGradioASGI

MODULE_PATHS = {
    "dashboard": "/app/dashboard",
    "market": "/app/market",
    "research": "/app/research",
    "strategy": "/app/strategy",
    "simulation": "/app/simulation",
    "live": "/app/live",
    "ai": "/app/ai",
    "knowledge": "/app/knowledge",
    "learning": "/app/learning",
    "admin": "/app/admin",
}


def _module_config(client, module: str) -> dict:
    response = client.get(f"{MODULE_PATHS[module]}/config")
    assert response.status_code == 200
    return response.json()


def _load_page_audit_runner():
    module_path = Path(__file__).with_name("page_audit_runner.py")
    spec = importlib.util.spec_from_file_location("page_audit_runner", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gradio_frontend_is_mounted(client):
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307
    assert root.headers["location"] == "/app/"

    slashless = client.get("/app", follow_redirects=False)
    assert slashless.status_code == 307
    assert slashless.headers["location"] == "/app/"

    page = client.get("/app/")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")

    shell_payload = client.get("/app/config").json()
    assert shell_payload["mode"] == "blocks"
    assert len(shell_payload["components"]) < 20
    shell_markup = "\n".join(
        str(component.get("props", {}).get("value", "")) for component in shell_payload["components"]
    )
    assert "quant-workspace-shell" in shell_markup
    assert all(f"data-workspace-module='{module}'" in shell_markup for module in MODULE_PATHS if module != "research")
    assert all(
        f"data-workspace-view-module='{module}'" in shell_markup for module in MODULE_PATHS if module != "research"
    )
    assert "data-workspace-module='research'" not in shell_markup
    assert "工作流中心" in shell_markup
    assert "app-language-toggle" in shell_markup
    assert "app-theme-toggle" in shell_markup
    assert "workspace-sidebar-toggle" in shell_markup
    assert "aria-controls='workspace-sidebar'" in shell_markup
    assert "https://github.com/charliedream1/ai_quant_trade" in shell_markup
    assert "https://gitee.com/charlie1/ai_quant_trade.git" in shell_markup
    assert "https://t.zsxq.com/dHt9l" in shell_markup
    assert "data-icon='market'" in shell_markup
    assert "iframe" not in shell_markup

    help_page = client.get("/help-docs/")
    assert help_page.status_code == 200
    assert "AIQuant智投帮助文档" in help_page.text

    payload = _module_config(client, "dashboard")
    assert payload["mode"] == "blocks"
    assert 50 < len(payload["components"]) < 400
    dashboard_element_ids = {component.get("props", {}).get("elem_id") for component in payload["components"]}
    assert "dashboard-ai-workbench-entry" in dashboard_element_ids
    market_bridge = next(
        component
        for component in payload["components"]
        if component.get("props", {}).get("elem_id") == "market-switcher"
    )
    assert market_bridge["props"].get("value") is None

    ai_payload = _module_config(client, "ai")
    element_ids = {component.get("props", {}).get("elem_id") for component in ai_payload["components"]}
    assert {
        "ai-command-center",
        "ai-floating-button",
        "ai-floating-panel",
        "ai-chat-history",
        "ai-workbench-chat-history",
        "ai-workbench-overview",
        "ai-console-chat-history",
    } <= element_ids

    strategy_payload = _module_config(client, "strategy")
    strategy_element_ids = {component.get("props", {}).get("elem_id") for component in strategy_payload["components"]}
    assert "ai-factor-mining" in strategy_element_ids
    admin_payload = _module_config(client, "admin")
    admin_element_ids = {component.get("props", {}).get("elem_id") for component in admin_payload["components"]}
    assert "help-docs-panel" in admin_element_ids

    labels = {
        component.get("props", {}).get("label")
        for component in ai_payload["components"]
        if component.get("props", {}).get("label")
    }
    assert {"账户视角", "任务类型", "专家", "专家分组", "任务模板"} <= labels
    assert "闭环模式" not in labels and "SOP" not in labels
    analysis_labels = {
        component.get("props", {}).get("label") for component in _module_config(client, "simulation")["components"]
    }
    assert {"分析来源", "SOP"} <= analysis_labels
    component_values = {
        str(component.get("props", {}).get("value"))
        for component in ai_payload["components"]
        if component.get("props", {}).get("value") is not None
    }
    assert {"开启任务", "关闭任务"} <= labels | component_values
    assert "新增或编辑MCP服务" in str(ai_payload) and "登记或配置Skill" in str(ai_payload)
    assert "登记Skill" in str(admin_payload)
    knowledge_payload = _module_config(client, "knowledge")
    knowledge_values = {str(component.get("props", {}).get("value")) for component in knowledge_payload["components"]}
    assert {"保存笔记", "上传入库"} <= knowledge_values
    task_type_choices: set[str] = set()
    for component in ai_payload["components"]:
        props = component.get("props", {})
        if props.get("label") != "任务类型":
            continue
        for choice in props.get("choices") or []:
            value = choice[1] if isinstance(choice, list | tuple) and len(choice) > 1 else choice
            task_type_choices.add(str(value))
    assert {
        "backtest",
        "paper_check",
        "calendar_refresh",
        "calendar_reference_refresh",
        "calendar_announcement_profile_check",
        "system_health_check",
        "data_maintain",
        "kb_sync",
    } <= task_type_choices
    chat_component = next(
        component
        for component in ai_payload["components"]
        if component.get("props", {}).get("elem_id") == "ai-chat-history"
    )
    assert chat_component["props"].get("type", "messages") == "messages"
    load_dependencies = [
        dependency
        for dependency in payload["dependencies"]
        if any(target[1] == "load" for target in dependency.get("targets") or [])
    ]
    assert len(load_dependencies) >= 3
    assert all(dependency["queue"] is False for dependency in load_dependencies)


def test_skill_registration_stores_contract_without_execution(client):
    from src.frontend.services import FrontendService

    status, rows = FrontendService().create_skill(
        "task14_safe_skill",
        "仅登记参数契约",
        "测试",
        '{"type":"object","properties":{"limit":{"type":"integer"}}}',
        '{"limit":5}',
    )

    assert "不执行上传代码" in status
    assert "task14_safe_skill" in rows.to_string()


def test_modular_gradio_builds_only_the_requested_app(client):
    mounts = {
        route.path: route.app
        for route in client.app.routes
        if getattr(route, "path", None) in set(MODULE_PATHS.values())
    }
    assert set(mounts) == set(MODULE_PATHS.values())
    assert all(not mounted.is_built for mounted in mounts.values())
    assert all(not mounted.is_started for mounted in mounts.values())

    assert client.get("/app/market/config").status_code == 200

    assert mounts["/app/market"].is_built
    assert mounts["/app/market"].is_started
    assert all(not mounted.is_built for path, mounted in mounts.items() if path != "/app/market")
    assert all(not mounted.is_started for path, mounted in mounts.items() if path != "/app/market")


def test_workspace_shell_is_independent_and_keeps_a_bounded_client_cache(client):
    from src.frontend.mounting import SHELL_FRONTEND_MOUNT_PATH
    from src.frontend.shell import SHELL_CACHE_LIMIT, SHELL_JS, SHELL_RUNTIME_JS

    shell_mount = next(
        route.app
        for route in client.app.routes
        if getattr(route, "path", None) == SHELL_FRONTEND_MOUNT_PATH and isinstance(route.app, LazyGradioASGI)
    )
    module_mounts = [
        route.app
        for route in client.app.routes
        if getattr(route, "path", None) in set(MODULE_PATHS.values()) and isinstance(route.app, LazyGradioASGI)
    ]

    assert not shell_mount.is_built
    assert all(not mounted.is_built for mounted in module_mounts)
    assert client.get("/app/config").status_code == 200
    assert shell_mount.is_built
    assert all(not mounted.is_built for mounted in module_mounts)
    assert SHELL_CACHE_LIMIT == 3
    assert 'document.createElement("iframe")' in SHELL_JS
    assert "while (frames.size > cacheLimit)" in SHELL_JS
    assert "history.pushState" in SHELL_JS
    assert "aiquant:select-view" in SHELL_JS
    assert "I18N_STORAGE_KEY" in SHELL_RUNTIME_JS
    assert "aiquant:theme" in SHELL_JS


@pytest.mark.asyncio
async def test_lazy_gradio_startup_runs_once_under_concurrent_requests():
    class FakeBlocks:
        def __init__(self) -> None:
            self.start_calls = 0
            self.extra_start_calls = 0
            self.close_calls = 0

        def run_startup_events(self) -> None:
            self.start_calls += 1

        async def run_extra_startup_events(self) -> None:
            self.extra_start_calls += 1

        def close(self, verbose: bool = True) -> None:
            self.close_calls += 1

    class FakeApp:
        def __init__(self) -> None:
            self.calls = 0

        async def __call__(self, scope, receive, send) -> None:
            self.calls += 1

    mounted = LazyGradioASGI(SimpleNamespace(), SimpleNamespace(info=lambda *args: None), "/app/test", "test")
    blocks = FakeBlocks()
    app = FakeApp()
    mounted._blocks = blocks
    mounted._app = app

    async def receive():
        return {"type": "http.disconnect"}

    async def send(message):
        return None

    await asyncio.gather(
        mounted({"type": "http"}, receive, send),
        mounted({"type": "http"}, receive, send),
    )

    assert mounted.is_started
    assert blocks.start_calls == 1
    assert blocks.extra_start_calls == 1
    assert app.calls == 2

    mounted.shutdown()

    assert not mounted.is_started
    assert blocks.close_calls == 1


def test_page_audit_runner_reports_gate_failures():
    audit_runner = _load_page_audit_runner()
    summary = {
        "results": [
            {"name": "ok_page", "status": "ok", "metrics": {"overflowCount": 0}},
            {"name": "wide_page", "status": "ok", "metrics": {"overflowCount": 2}},
            {"name": "missing_text", "status": "failed", "errors": ["expected text not visible: 今日必须看"]},
        ],
        "console_errors": ["Uncaught TypeError"],
        "http_errors": ["500 http://127.0.0.1/api/demo"],
    }

    failures = audit_runner.collect_audit_failures(summary)

    assert "wide_page: horizontal overflow count 2" in failures
    assert "missing_text: expected text not visible: 今日必须看" in failures
    assert "console: Uncaught TypeError" in failures
    assert "http: 500 http://127.0.0.1/api/demo" in failures


def test_page_audit_runner_only_ignores_known_errors_during_navigation():
    audit_runner = _load_page_audit_runner()

    assert audit_runner.is_navigation_console_noise("AbortError: BodyStreamBuffer was aborted")
    assert audit_runner.is_navigation_console_noise("Unexpected error Connection errored out. ")
    assert audit_runner.is_navigation_console_noise("TypeError: Failed to fetch")
    assert not audit_runner.is_navigation_console_noise("Uncaught TypeError: render failed")


def test_page_audit_runner_targets_modular_routes_and_tabs():
    audit_runner = _load_page_audit_runner()

    assert audit_runner.module_url("http://127.0.0.1:8013/app/dashboard/", "market") == (
        "http://127.0.0.1:8013/app/market/"
    )
    strategy = next(item for item in audit_runner.SCENARIOS if item["name"] == "10_strategy_lifecycle")
    simulation = next(item for item in audit_runner.SCENARIOS if item["name"] == "14_backtest")
    assert audit_runner.scenario_module(strategy["name"]) == "strategy"
    assert audit_runner.modular_tabs(strategy, "strategy") == ["策略构建", "策略管理", "生命周期"]
    assert audit_runner.modular_tabs(simulation, "simulation") == ["策略仿真", "回测与模拟", "回测"]
    assert all(audit_runner.scenario_module(item["name"]) for item in audit_runner.SCENARIOS)


def test_frontend_layout_keeps_navigation_and_data_readable(client):
    from src.frontend.registry import MODULES

    configs_by_module = {module: _module_config(client, module) for module in MODULE_PATHS}
    configs = list(configs_by_module.values())
    components = [component for config in configs for component in config["components"]]

    for module in MODULES:
        labels = {
            str(component.get("props", {}).get("label"))
            for component in configs_by_module[module.key]["components"]
            if component.get("props", {}).get("label")
        }
        assert {label for _, label in module.views} <= labels

    for module_key, config in configs_by_module.items():
        navigation = next(
            component
            for component in config["components"]
            if component.get("props", {}).get("elem_id") == "main-navigation"
        )
        assert navigation["type"] == "tabs"
        # Report buttons are intentionally stable on first entry. The duplicate
        # 54 KiB runtime initializer was removed, keeping the original byte budget.
        # Strategy adds provider controls for Alpha; preserve its existing JSON
        # byte limit below so native availability checks cannot grow startup data.
        assert len(config["components"]) < (450 if module_key == "ai" else 420 if module_key == "strategy" else 400)
        # The new workshop navigation metadata is shared with AI; its controls remain lazy.
        # Gradio 6.16 adds HTML/transport metadata; the graph stays absent from the initial tree.
        assert len(json.dumps(config, ensure_ascii=False)) < (646_000 if module_key == "ai" else 644_000), module_key
        assert not any(c.get("props", {}).get("elem_id") == "strategy-graph-editor" for c in config["components"])

    initial_ai_buttons = {
        component.get("props", {}).get("value")
        for component in configs_by_module["ai"]["components"]
        if component["type"] == "button"
    }
    assert "Market Review · 市场复盘" in initial_ai_buttons
    assert "Single Stock Analysis · 个股分析" in initial_ai_buttons

    serialized = str(configs)
    assert all(
        label in serialized
        for label in [
            "投研看板",
            "AI工作台",
            "知识与资料",
            "帮助",
            "模拟模块",
            "实盘模块",
            "智能洞察",
            "工作流中心",
            "因子研究与监控",
            "Qlib实验",
            "登记Workflow运行",
            "生命周期",
            "策略版本对比",
            "生成策略版本对比",
            "策略一键回测",
            "参数 schema 辅助编辑",
            "追加参数字段",
            "从源码提取参数",
            "运行归因",
            "每日行情",
            "分层收益时序",
            "风格暴露",
            "回测证据与模拟衔接",
            "导出交易日志",
            "一键创建模拟账户",
            "订单与组合约束",
            "复权方式",
            "单票最大权重",
            "回测参数对比",
            "对比回测",
            "撮合挂单",
            "推荐候选验证",
            "生成条件模板",
            "推荐一键回测",
            "CLI 会话列表与失败重试",
            "刷新会话列表",
            "重试会话",
            "风控阈值编辑",
            "dry-run订单计划",
            "生成dry-run订单计划",
            "检查并启动",
            "运行前风控",
            "通道适配器与事件",
            "查看通道适配器",
            "事件类型",
            "写入通道事件",
            "发布验证门槛",
            "验证回测 ID",
            "验证模拟账户 ID",
            "查看发布验证",
            "发布验证",
            "异常告警",
            "运行日志",
            "校验变量",
            "删除变量",
            "Parquet 行情湖目录",
            "DuckDB 查询库路径",
            "配置来源",
            "存储选型",
            "行情湖状态",
        ]
    )

    dataframes = [
        component
        for component in components
        if component["type"] == "dataframe" and component["props"].get("visible", True) is not False
    ]
    assert dataframes
    from src.frontend.common.navigation import navigation_config

    catalogs = [component for component in dataframes if component["props"].get("label") == "报告目录"]
    assert catalogs and all(
        component["props"]["max_height"] == navigation_config()["report_library"]["catalog_height"]
        for component in catalogs
    )
    assert all(
        component["props"].get("max_height", component["props"].get("height", 0)) >= 520
        for component in dataframes
        if component not in catalogs
    )
    assert all("data-table" in component["props"].get("elem_classes", []) for component in dataframes)
    if "wrap" in inspect.signature(gr.Dataframe).parameters:
        assert all(component["props"].get("wrap") is True for component in dataframes)
    from src.frontend.app import CSS

    assert "#market-switcher-row" in CSS
    assert "display: none !important" in CSS
    if "js" in inspect.signature(gr.mount_gradio_app).parameters:
        from src.frontend.app import APP_JS, gradio_mount_options

        assert gradio_mount_options()["js"] == APP_JS
        assert "colorizeTables" in APP_JS
        assert "normalizeLinks" in APP_JS
        assert "ai-workbench-main-tab" not in APP_JS
        assert "bindAiWorkbenchEntry" in APP_JS
        assert "findVisibleControl(\"#main-navigation [role='tab']\", text)" in APP_JS
        assert "\"#main-navigation button, #main-navigation [role='tab']\"" not in APP_JS
        assert "openAiFactorMining" in APP_JS
        assert "刷新因子挖掘" in APP_JS


def test_frontend_html_is_compressed(client):
    page = client.get("/app/dashboard/", headers={"Accept-Encoding": "gzip"})

    assert page.status_code == 200
    assert page.headers["content-encoding"] == "gzip"

    asset_reference = re.search(r'["\']([^"\']*/assets/[^"\']+\.js)["\']', page.text)
    assert asset_reference is not None
    asset = client.get(urljoin("/app/dashboard/", asset_reference.group(1)))
    assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_frontend_dashboard_uses_domain_services(client):
    from src.frontend.services import FrontendService

    (
        status,
        kpis,
        monitor,
        style,
        theme_chain,
        paths,
        actions,
        risk,
        holdings,
        account_plot,
        strategy_status,
        indices,
        watchlist,
        sector_plot,
    ) = FrontendService().dashboard()

    assert "系统状态" in status
    assert "最后刷新" in status
    assert "home-kpi-grid" in kpis
    assert not monitor.empty
    assert "module" in monitor.columns
    assert "情绪节点" in monitor.to_string()
    assert not style.empty
    assert "dimension" in style.columns
    assert not theme_chain.empty
    assert "chain_level" in theme_chain.columns
    assert not paths.empty
    assert "path" in paths.columns
    assert not actions.empty
    assert "priority" in actions.columns
    assert not risk.empty
    assert "metric" in risk.columns
    assert holdings.empty  # Empty portfolios do not fabricate holding rows.
    assert "symbol" in holdings.columns
    assert "实盘账户" in risk.to_string()
    assert account_plot.layout.title.text
    assert not strategy_status.empty
    assert "module" in strategy_status.columns
    assert not indices.empty
    assert "code" in indices.columns
    assert watchlist is not None
    assert "symbol" in watchlist.columns
    assert len(sector_plot.data) == 1

    live_status, _, _, _, _, _, _, live_risk, live_holdings, live_plot, *_ = FrontendService().dashboard("live")
    assert "当前视角" in live_status
    assert "实盘账户" in live_status
    assert "当前视角" in live_risk.to_string()
    assert live_holdings.empty  # Configured capital is not a broker holding.
    assert live_plot.layout.title.text

    summary_status, summary_kpis = FrontendService().dashboard_summary("paper")
    assert "分块加载" in summary_status
    assert "home-kpi-grid" in summary_kpis
    assert "账户总资产" in summary_kpis
    assert "今日盈亏" in summary_kpis
    assert "dashboard-signal-board" not in summary_kpis
    live_summary_status, live_summary_kpis = FrontendService().dashboard_summary("live")
    assert "实盘账户" in live_summary_status
    assert "待 broker 回传" in live_summary_kpis
    assert "home-kpi-grid" in live_summary_kpis
    assert "账户总资产" in live_summary_kpis
    ai_entry = FrontendService().dashboard_ai_workbench_entry("paper")
    assert "ai-dashboard-entry" in ai_entry
    assert "进入 AI 工作台" in ai_entry
    focus_html, pnl_plot = FrontendService().dashboard_account_focus("paper")
    assert "dashboard-focus-panel" in focus_html
    assert pnl_plot.layout.title.text
    market_brief, news_cards = FrontendService().dashboard_market_brief("paper")
    assert "dashboard-market-panel" in market_brief
    assert "dashboard-news-panel" in news_cards
    market = FrontendService().dashboard_market("paper")
    assert len(market) == 7
    assert not market[0].empty
    account = FrontendService().dashboard_account("paper")
    assert len(account) == 3
    assert not account[0].empty
    trades = FrontendService().dashboard_trade_history("paper")
    assert not trades.empty
    assert {"symbol", "status", "source"} <= set(trades.columns)
    strategy = FrontendService().dashboard_strategy("paper")
    assert len(strategy) == 2
    assert not strategy[0].empty


def _plain_frame(value):
    """Unwrap pandas Styler objects returned with color-scale styling."""

    import pandas.io.formats.style as pd_style

    return value.data if isinstance(value, pd_style.Styler) else value


def test_frontend_visualizations_are_populated(client, tmp_path):
    from src.frontend.services import FrontendService

    frontend = FrontendService()

    indices, sectors, market_plot = frontend.market_overview("industry", 20)
    assert not _plain_frame(indices).empty
    assert not _plain_frame(sectors).empty
    assert len(market_plot.data) == 1
    assert market_plot.data[0].orientation == "h"

    (
        factor_status,
        factor_kpis,
        factor_ic_plot,
        factor_quantile_plot,
        factor_diagnostic_plot,
        factor_quantile_history_plot,
        factor_style_exposure_plot,
    ) = frontend.factor_monitor_summary(
        "600519,300750,000001,688981,300124",
        force_refresh=True,
    )
    assert "因子监控" in factor_status
    assert "dashboard-card" in factor_kpis
    assert factor_ic_plot.layout.title.text
    assert factor_quantile_plot.layout.title.text
    assert factor_diagnostic_plot.layout.title.text
    assert factor_quantile_history_plot.layout.title.text
    assert factor_style_exposure_plot.layout.title.text
    assert len(factor_diagnostic_plot.data) >= 1
    assert len(factor_quantile_history_plot.data) >= 1
    assert len(factor_style_exposure_plot.data) >= 1
    factor_metrics, factor_alerts, factor_snapshots, factor_corr_plot, qlib_status = frontend.factor_monitor_details(
        "600519,300750,000001"
    )
    assert not _plain_frame(factor_metrics).empty
    assert "factor_key" in _plain_frame(factor_metrics).columns
    assert "capacity_hint" in _plain_frame(factor_metrics).columns
    assert "rank_ic_std" in _plain_frame(factor_metrics).columns
    assert factor_alerts is not None
    assert not _plain_frame(factor_snapshots).empty
    assert factor_corr_plot.layout.title.text
    assert "Qlib状态" in qlib_status

    news, keyword_plot, status = frontend.news("全部", "", "")
    assert not news.empty
    assert len(keyword_plot.data) == 1
    assert "条新闻" in status
    assert "最后刷新" in status

    assert frontend.security_master_search("茅台", 5).iloc[0]["symbol"] == "600519"
    assert "600519" in frontend.security_master_search("guizhou", 5)["symbol"].tolist()
    _, score_plot, finance, kline_plot, _, _ = frontend.stock("贵州茅台", "daily", 60)
    assert len(score_plot.data) == 1
    assert not finance.empty
    assert {trace.type for trace in kline_plot.data} == {"bar", "candlestick", "scatter"}
    assert len(kline_plot.data) == 5
    stock_relation = frontend.stock_to_relations("600519", 2, ["industry"])
    assert stock_relation[1] == "600519"
    assert "图谱摘要" in stock_relation[2]

    relation_summary, relation_analysis, relation_paths, nodes, edges, relation_plot = frontend.relations(
        "茅台",
        3,
        [
            "industry",
            "concept",
            "supply_chain",
            "shareholder",
            "news_cooccurrence",
            "correlation",
            "task",
            "analysis",
        ],
    )
    assert "图谱摘要" in relation_summary
    assert "构建说明" in relation_summary
    assert "节点分组" in relation_summary
    assert "层级展开" in relation_summary
    assert not relation_analysis.empty
    assert "构建方式" in relation_analysis.to_string()
    assert "关系分组" in relation_analysis.to_string()
    assert "层级展开" in relation_analysis.to_string()
    assert not relation_paths.empty
    assert "path" in relation_paths.columns
    assert not nodes.empty
    assert max(int(value) for value in nodes["layer"]) >= 3
    assert "degree" in nodes.columns
    assert "layer" in nodes.columns
    assert "parent_id" in nodes.columns
    assert "path" in nodes.columns
    assert "group_label" in nodes.columns
    assert "关联行业" in nodes.to_string()
    assert not edges.empty
    assert "relation_label" in edges.columns
    assert {"产业链", "股东/机构", "分析构建"} & set(edges["relation_label"])
    assert len(relation_plot.data) >= 2
    expected_trace_limit = edges["relation_type"].nunique() + nodes["type"].nunique()
    assert len(relation_plot.data) <= expected_trace_limit
    export_status, export_path = frontend.export_relations("600519", 2, ["industry", "analysis"])
    assert "关系图谱已导出" in export_status
    exported = Path(export_path)
    assert exported.exists()
    assert '"nodes"' in exported.read_text(encoding="utf-8")

    recommend_status, recommend_rows = frontend.recommend("momentum", "quick", 3, "")
    assert "方案说明" in recommend_status
    assert not recommend_rows.empty
    assert {"方案", "推荐理由", "动量", "流动性", "情绪", "缠论", "入选时间"} <= set(recommend_rows.columns)
    assert "趋势动量" in set(recommend_rows["方案"])
    assert "T" not in str(recommend_rows.iloc[0]["入选时间"])
    recommend_template = frontend.recommend_condition_template("momentum", "quick", 3, "")
    assert "推荐条件模板" in recommend_template
    assert "20 日动量" in recommend_template
    template_status, template_rows = frontend.recommend_save_template(
        "动量观察模板", "momentum", "quick", 3, "600519,300750"
    )
    assert "已保存" in template_status
    template_row = template_rows[template_rows["name"] == "动量观察模板"].iloc[0]
    load_status, load_plan, load_path, load_limit, load_universe = frontend.recommend_load_template(
        int(template_row["id"])
    )
    assert "已加载推荐模板" in load_status
    assert load_plan == "momentum"
    assert load_path == "quick"
    assert load_limit == 3
    assert "600519" in load_universe
    compare_status, compare_rows, compare_figure = frontend.recommend_candidate_compare(recommend_rows, "")
    assert "候选的对比视图" in compare_status
    assert not compare_rows.empty
    assert {"优势因子", "验证动作", "回测标的"} <= set(compare_rows.columns)
    assert len(compare_figure.data) >= 3
    group_status, group_summary, group_symbols, group_figure = frontend.recommend_group_compare(
        ["balanced", "momentum", "quality"],
        "quick",
        3,
        "",
    )
    assert "横向对比" in group_status
    assert not group_summary.empty
    assert {"方案", "平均评分", "重合候选"} <= set(group_summary.columns)
    assert not group_symbols.empty
    assert {"出现组数", "覆盖方案", "建议动作"} <= set(group_symbols.columns)
    assert len(group_figure.data) >= 2
    watch_message, watch_groups, watch_quotes = frontend.add_recommendations_to_watchlist(0, recommend_rows, "")
    assert "推荐结果已加入自选分组" in watch_message
    assert not watch_groups.empty
    assert set(recommend_rows["代码"]) <= set(watch_quotes["symbol"])
    resource_status, resource_pools, resource_items = frontend.add_recommendations_to_resource_pool(
        0, recommend_rows, ""
    )
    assert "推荐候选已加入资源池" in resource_status
    assert not resource_pools.empty
    assert set(recommend_rows["代码"]) <= set(resource_items["symbol"])
    load_resource_status, universe_text, loaded_items = frontend.resource_pool_to_universe(
        int(resource_items.iloc[0]["pool_id"])
    )
    assert "已载入资源池" in load_resource_status
    assert str(recommend_rows.iloc[0]["代码"]) in universe_text
    assert not loaded_items.empty
    import pandas as pd

    resource_file = tmp_path / "resource_pool.xlsx"
    pd.DataFrame(
        {
            "证券代码": ["600519", "300750"],
            "名称": ["贵州茅台", "宁德时代"],
            "权重": [0.6, 0.4],
            "备注": ["核心", "新能源"],
        }
    ).to_excel(
        resource_file,
        index=False,
    )
    import_status, _, imported_items = frontend.import_resource_pool_file(
        int(resource_items.iloc[0]["pool_id"]),
        str(resource_file),
    )
    assert "已导入" in import_status
    assert {"600519", "300750"} <= set(imported_items["symbol"])
    recommend_relation = frontend.recommend_first_to_relations(recommend_rows, "", 2, ["industry"])
    assert recommend_relation[1] == str(recommend_rows.iloc[0]["代码"])
    assert "图谱摘要" in recommend_relation[2]

    _, universe_rows = frontend.recommend("balanced", "quick", 5, "600519, 非法代码")
    assert list(universe_rows["代码"]) == ["600519"]
    chan_status, chan_rows = frontend.recommend("chan", "quick", 2, "600519")
    assert "缠论结构" in chan_status
    assert not chan_rows.empty
    assert "缠论" in chan_rows.columns

    learning_rows = frontend.learning_catalog("all", "")
    assert not learning_rows.empty
    assert "chapter_id" in learning_rows.columns
    learning_detail = frontend.learning_detail(int(learning_rows.iloc[0]["chapter_id"]))
    assert "来源" in learning_detail
    assert "最后刷新" in learning_detail

    from src.help_docs import help_docs_iframe_html

    assert "/help-docs/" in help_docs_iframe_html()

    preset_rows = frontend.preset_strategies()
    assert not preset_rows.empty
    assert "path" in preset_rows.columns

    cli_session, cli_logs, cli_artifacts = frontend.cli_build("codex", "生成一个低换手趋势策略")
    assert '"cli_type": "codex"' in cli_session
    assert "codex cli" in cli_logs
    assert not cli_artifacts.empty
    cli_sessions = frontend.cli_sessions()
    assert "codex" in cli_sessions.to_string()
    retry_session, retry_logs, retry_artifacts, retry_sessions = frontend.cli_retry(
        int(json.loads(cli_session)["session_id"])
    )
    assert "retry_from" in retry_logs
    assert int(json.loads(retry_session)["session_id"]) > int(json.loads(cli_session)["session_id"])
    assert not retry_artifacts.empty
    assert len(retry_sessions) >= 2
    _, _, _, refreshed_sessions = frontend.cli_build_with_sessions("trae", "生成一个均线策略")
    assert not refreshed_sessions.empty
    assert "trae" in refreshed_sessions.to_string()


def test_frontend_core_workflows(client, keyword_model):
    from src.frontend.services import FrontendService

    frontend = FrontendService()
    group_message, groups = frontend.create_watchlist_group("gradio_watch", 1)
    group_id = int(groups.iloc[0]["id"])
    assert "已创建" in group_message
    watch_message, _, watch_quotes = frontend.add_watchlist_symbols(group_id, "600519")
    assert "已加入" in watch_message
    assert not watch_quotes.empty
    assert "贵州茅台" in watch_quotes.to_string()
    remove_message, _, watch_quotes = frontend.remove_watchlist_symbol(group_id, "600519")
    assert "已从分组" in remove_message
    assert watch_quotes.empty or "600519" not in watch_quotes.to_string()

    news, _, _ = frontend.news("全部", "", "")
    news_detail = frontend.news_detail(int(news.iloc[0]["id"]))
    assert "来源" in news_detail

    reports = frontend.research_reports("", "")
    assert not reports.empty
    assert "link" in reports.columns
    assert "已保存" in frontend.save_research_report(int(reports.iloc[0]["id"]))
    papers = frontend.paper_search("Factor", "", "", "")
    assert not papers.empty
    assert "已导入知识库" in frontend.import_paper_to_kb(int(papers.iloc[0]["id"]))

    source = Path("egs/examples/strategy_examples/dual_ma_strategy.py").read_text(encoding="utf-8")
    extract_status, extracted_params, extracted_rows = frontend.strategy_param_schema_extract(source, None)
    assert "已从源码提取" in extract_status
    assert json.loads(extracted_params)["fast_window"] == 5
    assert "fast_window" in extracted_rows.to_string()
    add_status, edited_params, param_rows = frontend.strategy_param_schema_add(
        extracted_params,
        "enabled",
        "bool",
        "true",
        "是否启用",
    )
    assert "enabled" in add_status
    assert json.loads(edited_params)["enabled"] is True
    assert "是否启用" in param_rows.to_string()
    preview_status, preview_params, preview_rows = frontend.strategy_param_schema_preview(edited_params)
    assert "参数预览" in preview_status
    assert json.loads(preview_params)["slow_window"] == 20
    assert not preview_rows.empty
    message, strategies = frontend.create_strategy(
        "gradio_flow", "v1", "frontend test", "trend", edited_params, source, None
    )
    strategy_id = int(strategies.iloc[0]["strategy_id"])
    assert "已入库" in message
    message_v2, _ = frontend.create_strategy("gradio_flow", "v2", "frontend test v2", "trend", "{}", source, None)
    assert "v2" in message_v2
    version_status, version_rows = frontend.strategy_version_compare(strategy_id)
    assert "策略版本对比" in version_status
    assert not version_rows.empty
    assert {"策略ID", "版本", "最近回测"} <= set(version_rows.columns)
    assert len(version_rows) >= 2
    from src.strategy.strategy_store import StrategyStore

    stored_source = StrategyStore().get(strategy_id)
    StrategyStore().review(strategy_id, stored_source["source_sha256"], "explicit-frontend-test-review")
    quick_backtest = frontend.strategy_quick_backtest(
        strategy_id,
        "600519,300750",
        "2026-01-01",
        "2026-03-01",
        1000000,
        "{}",
        "simple",
    )
    assert "策略一键回测已完成" in quick_backtest[0]
    assert quick_backtest[1] > 0
    assert not quick_backtest[2].empty
    assert "finished" in quick_backtest[3].to_string()
    assert "已删除" in frontend.delete_backtest(quick_backtest[1])[0]

    _, recommend_rows = frontend.recommend("momentum", "quick", 3, "600519,300750")
    recommend_backtest = frontend.recommend_to_backtest(
        strategy_id,
        recommend_rows,
        "",
        "2026-01-01",
        "2026-03-01",
        1000000,
        "{}",
        "simple",
    )
    assert "股票池来自推荐候选" in recommend_backtest[0]
    assert recommend_backtest[1] > 0
    assert not recommend_backtest[2].empty
    assert not recommend_backtest[6].empty
    assert "已删除" in frontend.delete_backtest(recommend_backtest[1])[0]

    backtest = frontend.create_backtest(
        strategy_id,
        "600519,300750",
        "2026-01-01",
        "2026-03-01",
        1000000,
        "{}",
        "simple",
        "market",
        "qfq",
        3,
        0.3,
        100,
        0.001,
    )
    assert backtest[1] > 0
    assert not backtest[3].empty
    assert not backtest[7].empty
    assert "标的贡献" in backtest[7].to_string()
    assert "订单类型" in backtest[3].to_string()
    assert "qfq" in backtest[3].to_string()
    assert "order_type" in backtest[5].columns
    snapshot = frontend.backtest_param_snapshot(backtest[1])
    assert "回测参数快照" in snapshot
    assert "初始资金" in snapshot
    assert "成交假设" in snapshot
    assert "单票 30.00%" in snapshot
    export_message, export_path = frontend.export_backtest_trades(backtest[1])
    assert "已导出" in export_message
    assert export_path is not None
    assert Path(export_path).exists()
    assert "symbol" in Path(export_path).read_text(encoding="utf-8-sig")
    compare_status, compare_rows, compare_figure, compare_params = frontend.compare_backtests(str(backtest[1]), 5)
    assert "已对比" in compare_status
    assert not compare_rows.empty
    assert "总收益" in compare_rows.columns
    assert "订单类型" in compare_rows.columns
    assert len(compare_figure.data) >= 3
    assert not compare_params.empty
    assert "组合约束" in compare_params.columns
    paper_from_backtest = frontend.backtest_to_paper_account(backtest[1], "", None)
    assert paper_from_backtest[1] > 0
    assert "模拟账户已创建" in paper_from_backtest[0]

    account = frontend.create_paper_account("gradio_paper", strategy_id, 1000000)
    account_id = account[1]
    order = frontend.paper_order(account_id, "600519", "buy", "market", None, 100)
    assert "已成交" in order[0]
    assert not order[2].empty
    pending_order = frontend.paper_order(account_id, "600519", "buy", "limit", 1, 100)
    assert "待撮合" in pending_order[0]
    assert "待撮合" in pending_order[3].to_string()
    matched_order = frontend.paper_match_orders(account_id)
    assert "成交 0 笔" in matched_order[0]

    missing_message, missing_configs = frontend.create_live_config(
        "gradio_live_missing", strategy_id, "paper", 100000, "{}", "{}"
    )
    missing_config_id = int(missing_configs.iloc[0]["config_id"])
    assert "已创建" in missing_message
    frontend.update_live_risk(
        missing_config_id,
        '{"max_position_count": 3, "daily_loss_limit": 0.02}',
    )
    missing_blocked = frontend.live_precheck_start(missing_config_id, "000001,300750", "买入", "市价", 0.5, 2)
    assert "运行前风控拦截" in missing_blocked[0]
    assert "回测验证" in missing_blocked[7].to_string()
    assert "模拟验证" in missing_blocked[7].to_string()

    live_message, live_configs = frontend.create_live_config(
        "gradio_live", strategy_id, "paper", 100000, "{}", "{}", backtest[1], account_id
    )
    config_id = int(live_configs.iloc[0]["config_id"])
    assert "已创建" in live_message
    validation_rows = frontend.live_validation_summary(config_id)
    assert "回测验证" in validation_rows.to_string()
    assert "模拟验证" in validation_rows.to_string()
    assert "拦截" not in validation_rows.to_string()
    risk_message, live_configs, risk_rows = frontend.update_live_risk(
        config_id,
        '{"max_position_count": 3, "daily_loss_limit": 0.02}',
    )
    assert "风控阈值已更新" in risk_message
    assert "最大持仓数" in risk_rows.to_string()
    assert "2.00%" in risk_rows.to_string()
    plan_status, plan_orders, precheck_rows = frontend.live_dry_run_plan(
        config_id,
        "000001,300750",
        "买入",
        "市价",
        0.5,
        2,
    )
    assert "dry-run订单计划" in plan_status
    assert "运行前风控" in plan_status
    assert not plan_orders.empty
    assert "通过" in precheck_rows.to_string()
    blocked = frontend.live_precheck_start(config_id, "600519", "买入", "市价", 0.01, 1)
    assert "运行前风控拦截" in blocked[0]
    assert blocked[1] == 0
    assert "行情与手数" in blocked[7].to_string()
    run = frontend.live_precheck_start(config_id, "000001,300750", "买入", "市价", 0.5, 2)
    assert run[1] > 0
    assert "风控检查已通过" in run[0]
    assert "运行中" in run[2]
    status_json, status_orders, status_positions = frontend.live_status(run[1])
    assert "status_label" in status_json
    assert "运行中" in status_json
    assert not status_orders.empty
    assert not status_positions.empty
    assert not frontend.live_runs().empty
    adapter_rows = frontend.live_broker_adapters()
    assert not adapter_rows.empty
    assert {"paper", "broker"} <= set(adapter_rows["channel"])
    assert bool(adapter_rows[adapter_rows["channel"] == "broker"].iloc[0]["available"]) is False
    heartbeat_event = frontend.live_broker_event(run[1], "heartbeat", "")
    assert "心跳刷新" in heartbeat_event[0]
    assert "heartbeat" in heartbeat_event[1]
    event_frozen = frontend.live_broker_event(run[1], "error", "broker心跳中断")
    assert "异常冻结" in event_frozen[0]
    assert "broker心跳中断" in event_frozen[1]
    event_recovered = frontend.live_resume(run[1])
    assert "运行中" in event_recovered[1]
    paused = frontend.live_pause(run[1])
    assert "已暂停" in paused[0]
    assert "已暂停" in paused[1]
    resumed = frontend.live_resume(run[1])
    assert "已恢复" in resumed[0]
    assert "运行中" in resumed[1]
    frozen = frontend.live_mark_error(run[1], "人工演练异常")
    assert "异常冻结" in frozen[0]
    assert "人工演练异常" in frozen[1]
    frozen_monitor_summary, frozen_alerts, frozen_logs = frontend.live_monitor(run[1])
    assert "错误" in frozen_monitor_summary
    assert "人工演练异常" in frozen_alerts.to_string()
    assert "运行错误" in frozen_logs.to_string()
    recovered = frontend.live_resume(run[1])
    assert "运行中" in recovered[1]
    live_monitor_summary, live_alerts, live_logs = frontend.live_monitor(run[1])
    assert "最近心跳" in live_monitor_summary
    assert "运行中" in live_monitor_summary
    assert not live_alerts.empty
    assert "暂无异常告警" in live_alerts.to_string()
    assert not live_logs.empty
    assert "最近心跳" in live_logs.to_string()
    lifecycle_summary, lifecycle_board, lifecycle_rows = frontend.strategy_lifecycle()
    assert "策略生命周期" in lifecycle_summary
    assert "strategy-lifecycle-board" in lifecycle_board
    lifecycle_row = lifecycle_rows[lifecycle_rows["strategy_id"] == strategy_id]
    assert not lifecycle_row.empty
    assert lifecycle_row.iloc[0]["stage"] == "实盘候选"
    stopped = frontend.live_stop(run[1])
    assert "已停止" in stopped[0]
    assert "已停止" in stopped[1]
    delete_backtest = frontend.delete_backtest(backtest[1])
    assert "已删除" in delete_backtest[0]

    qlib_status, qlib_config, qlib_runs = frontend.qlib_workflow_status("workflow")
    assert "Qlib实验状态" in qlib_status
    assert not qlib_config.empty
    qlib_message, qlib_runs = frontend.qlib_workflow_create_run(
        "workflow",
        "",
        "",
        '{"experiment_name": "frontend_qlib"}',
    )
    assert "已处理" in qlib_message
    assert not qlib_runs.empty
    assert "frontend_qlib" in qlib_runs.to_string()

    category_message, categories = frontend.create_category("Gradio 分类", 0)
    category_id = int(categories.iloc[0]["id"])
    assert "已创建" in category_message
    note_message, documents = frontend.create_note("Gradio 笔记", category_id, "ui", "动量与趋势")
    assert "已保存" in note_message
    assert not documents.empty
    note_rows = documents[documents["title"] == "Gradio 笔记"]
    assert not note_rows.empty
    doc_id = int(note_rows.iloc[0]["doc_id"])
    note_detail = frontend.kb_document_detail(doc_id)
    assert "Gradio 笔记" in note_detail
    assert "分块数" in note_detail
    qa_status, qa_answer, qa_refs = frontend.kb_qa_session("动量是什么？", category_id, 3, "ui-session", False)
    assert "ui-session" in qa_status
    assert qa_answer
    assert not qa_refs.empty
    qa_sessions = frontend.kb_qa_sessions()
    assert "ui-session" in qa_sessions.to_string()
    save_session_status, qa_sessions = frontend.kb_qa_save_session("ui-session", "UI 动量会话", "前端知识问答会话摘要")
    assert "已保存" in save_session_status
    assert "UI 动量会话" in qa_sessions.to_string()
    assert "前端知识问答会话摘要" in qa_sessions.to_string()
    clear_status, clear_answer, clear_refs = frontend.kb_qa_clear("ui-session")
    assert "已清空" in clear_status
    assert clear_answer == ""
    assert "暂无数据" in clear_refs.to_string()
    with pytest.raises(ValueError, match="确认框"):
        frontend.kb_delete_document(doc_id, "", None, "all", "")
    delete_message, documents_after_delete, detail_after_delete, confirm_after_delete = frontend.kb_delete_document(
        doc_id, "", None, "all", "DELETE"
    )
    assert "已删除" in delete_message
    assert "Gradio 笔记" not in documents_after_delete.to_string()
    assert detail_after_delete == ""
    assert confirm_after_delete == ""

    job_message, jobs = frontend.create_job("gradio_job", "news_fetch", "*/10 * * * *", "{}", True)
    job_id = int(jobs.iloc[0]["job_id"])
    assert "已创建" in job_message
    result, _, history = frontend.job_action(job_id, "trigger")
    assert "history_id" in result
    assert not history.empty
    assert not frontend.job_histories(job_id).empty


def test_frontend_ai_workbench_presets_and_chat(client):
    from src.frontend.services import (
        AI_CONSOLE_BACKEND_CHOICES,
        AI_EXPERT_CHOICES,
        AI_JOB_TEMPLATE_CHOICES,
        AI_TEAM_CHOICES,
        QUANT_WORKFLOW_MODE_CHOICES,
        QUANT_WORKFLOW_SOP_CHOICES,
        FrontendService,
    )

    frontend = FrontendService()
    header = frontend.ai_workbench_header()
    assert "AI 工作台" in header
    assert "专家团" in header
    assert "闭环SOP" in header
    assert "因子挖掘" in header
    overview = frontend.ai_workbench_overview("paper")
    assert "ai-workbench-overview" in overview
    assert "最近闭环运行" in overview
    nav = frontend.ai_console_nav()
    assert {"新聊天", "定时任务", "Skill 包", "MCP 服务"} <= set(nav["入口"])
    assert {value for _, value in AI_CONSOLE_BACKEND_CHOICES} >= {"generic_agent", "codex", "trae", "workbuddy"}
    console_status, console_session_id, console_sessions, console_history = frontend.ai_console_new_session(
        "端到端分析",
        "money_maker",
    )
    assert "已新建会话" in console_status
    assert console_session_id > 0
    assert not console_sessions.empty
    assert console_history == []
    loaded_status, loaded_history = frontend.ai_console_load_session(console_session_id)
    assert "已载入会话" in loaded_status
    assert loaded_history == []
    returned_session_id, console_history, cleared_input, console_reply_status, console_sessions = (
        frontend.ai_console_send(
            console_session_id,
            "请总结当前资源池和图谱下一步",
            [],
        )
    )
    assert returned_session_id == console_session_id
    assert cleared_input == ""
    assert console_history[-1]["role"] == "assistant"
    assert "GenericAgent" in console_reply_status or "mock-llm" in console_reply_status
    assert str(console_session_id) in console_sessions.to_string()
    _, cli_history, _, cli_status, _ = frontend.ai_console_send(
        console_session_id,
        "用 codex cli 生成一个低换手策略骨架",
        console_history,
        "codex",
    )
    assert "mock 模式未执行真实 Codex CLI" in cli_history[-1]["content"]
    assert "mock 模式未执行真实 Codex CLI" in cli_status
    preview = frontend.ai_console_file_preview("README.md")
    assert "AIQuant" in preview or "量化" in preview
    project_status, project_tree, project_dir = frontend.ai_console_project_tree(".")
    assert "项目目录" in project_status
    assert project_dir == "."
    assert not project_tree.empty
    assert {"类型", "路径", "说明"} <= set(project_tree.columns)
    with pytest.raises(ValueError, match="只能访问项目目录内"):
        frontend.ai_console_project_tree("../")
    assert {value for _, value in QUANT_WORKFLOW_MODE_CHOICES} >= {"simulation", "live"}
    assert {value for _, value in QUANT_WORKFLOW_SOP_CHOICES} >= {"simulation_research_loop", "live_observation_loop"}

    experts = frontend.ai_experts("all")
    assert not experts.empty
    assert {"expert_id", "name", "focus", "starter", "deliverable"} <= set(experts.columns)
    expert_cards = frontend.ai_expert_cards("all")
    assert "ai-agent-card" in expert_cards
    assert "试试这个问题" in expert_cards

    expert_id = AI_EXPERT_CHOICES[0][1]
    detail = frontend.ai_expert_detail(expert_id)
    assert "###" in detail
    brief, context = frontend.ai_workbench_state("strategy", "paper", expert_id)
    assert "AI工作台" in brief
    assert "ai-context-board" in context
    task_type, selected_id, starter, brief = frontend.ai_expert_to_task(expert_id, "paper")
    assert selected_id == expert_id
    assert starter
    assert task_type
    assert "AI工作台" in brief

    history, cleared, status = frontend.ai_workbench_chat(task_type, "paper", expert_id, starter, [])
    assert cleared == ""
    assert history[-1]["role"] == "assistant"
    assert "mock-llm" in status

    teams = frontend.ai_teams("all")
    assert not teams.empty
    assert {"team_id", "lead", "members", "starter", "deliverable"} <= set(teams.columns)
    team_cards = frontend.ai_team_cards("all")
    assert "ai-team-card" in team_cards
    assert "负责人" in team_cards
    team_id = AI_TEAM_CHOICES[0][1]
    team_detail = frontend.ai_team_detail(team_id)
    assert "成员分工" in team_detail
    team_task_type, team_expert_id, team_prompt, _, team_context = frontend.ai_team_to_task_state(team_id, "paper")
    assert team_task_type
    assert team_expert_id
    assert "专家团" in team_prompt
    assert "协作模式" in team_context

    templates = frontend.ai_job_templates()
    assert not templates.empty
    template_cards = frontend.ai_job_template_cards()
    assert "ai-job-card" in template_cards
    name, job_type, cron, params, enabled = frontend.ai_job_template_form(AI_JOB_TEMPLATE_CHOICES[0][1])
    assert name
    assert job_type
    assert cron
    assert params.startswith("{")
    assert isinstance(enabled, bool)

    capability_cards, skills, mcps = frontend.ai_capability_catalog()
    assert "ai-capability-card" in capability_cards
    assert skills is not None
    assert mcps is not None

    workflow_cards = frontend.quant_workflow_sop_cards()
    assert "quant-flow-card" in workflow_cards
    assert "DataAgent" in workflow_cards
    summary, board, steps, insights, questions, advice, artifacts = frontend.quant_workflow_snapshot(
        "simulation",
        "simulation_research_loop",
        None,
        None,
        None,
        None,
    )
    assert "模拟研究闭环" in summary
    assert "quant-workflow-board" in board
    assert not steps.empty
    assert "step_order" in steps.columns
    assert questions is not None
    assert not advice.empty
    assert not artifacts.empty

    save_status, runs = frontend.quant_workflow_create_run(
        "simulation",
        "simulation_research_loop",
        "pytest 闭环",
        None,
        None,
        None,
        None,
    )
    assert "run_id" in save_status
    assert not runs.empty


def test_learning_tree_preset_detail_and_dashboard_layout():
    from src.frontend.services import DASHBOARD_MODULE_KEYS, FrontendService

    frontend = FrontendService()

    tree = frontend.learning_tree()
    assert tree, "学习目录不应为空"
    first_group = tree[0]
    first_chapter_id = int(first_group["chapters"][0][1])
    assert "最后刷新" in frontend.learning_detail(first_chapter_id)

    example_path = "egs/examples/strategy_examples/dual_ma_strategy.py"
    intro, code, params_yaml, meta = frontend.preset_strategy_detail(example_path)
    assert "双均线趋势策略" in intro
    assert "fast_window" in params_yaml
    assert "DualMovingAverageStrategy" in code
    assert '"valid": true' in meta

    with pytest.raises(ValueError):
        frontend.import_strategy_example(example_path, None, "", "fast_window: [")
    with pytest.raises(ValueError):
        frontend.save_dashboard_layout([])

    status = frontend.save_dashboard_layout(["kpis", "indices"])
    assert "布局已保存" in status
    assert frontend.load_dashboard_layout() == ["kpis", "indices"]
    runtime_status = frontend.system_runtime_status()
    assert "运行状态" in runtime_status
    assert "交易日历" in runtime_status
    assert "系统告警" in runtime_status
    frontend.save_dashboard_layout(DASHBOARD_MODULE_KEYS)
    assert frontend.load_dashboard_layout() == DASHBOARD_MODULE_KEYS
