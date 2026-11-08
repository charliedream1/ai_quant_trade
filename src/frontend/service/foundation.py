"""UI-facing service adapters.

The Gradio callbacks call the same domain services used by the REST routes.  This
keeps validation, persistence, and synthetic/live data behavior consistent
between both interfaces.
"""

from __future__ import annotations

# This module is the explicit dependency hub re-exported to domain service modules.
# ruff: noqa: F401
import copy
import json
import re
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from html import escape
from math import cos, pi, sin
from pathlib import Path
from threading import RLock
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import yaml
from plotly.subplots import make_subplots

from src.agent import GenericAgentRuntime, LLMClient, RAGService
from src.agent.composer_config import composer_config
from src.core.config import get_settings
from src.core.database import Database
from src.core.env_file import delete_env_value, env_status, import_env_file, masked_env_rows
from src.core.exceptions import BusinessError
from src.core.fts import FTSService, kb_document_source_scope, kb_remote_source_id
from src.core.kb_importer import import_uploaded_document
from src.core.logger import get_logger
from src.core.market_lake import MarketDataLake
from src.core.repository import Repository, json_loads
from src.core.system_settings import global_settings_payload, runtime_storage_rows, save_global_settings
from src.core.timeutil import utc_now_iso
from src.data import (
    DataSourceManager,
    SecurityMasterService,
    current_market,
    parse_security_symbols,
    set_current_market,
)
from src.engine.backtest import BacktestRunner
from src.engine.live import LiveBrokerEventService, LiveTradingService
from src.engine.market import (
    MarketReportGenerator,
    NewsAggregator,
    PaperSearchService,
    QuoteService,
    Recommender,
    RelationGraphService,
    ResourcePoolService,
    StockAnalyzer,
)
from src.engine.paper import PaperAccountService
from src.engine.research import FactorMonitorService, QlibWorkflowService, QuantWorkflowService
from src.frontend.common.errors import ui_error_message as _public_ui_error_message
from src.integration.mcp_client import MCPServiceManager
from src.integration.remote_sources.service import RemoteSourceService
from src.integration.skill_manager import SkillManager
from src.scheduler import SchedulerService
from src.scheduler.calendar_updater import trading_calendar_alerts, trading_calendar_status
from src.strategy import StrategyStore, StrategyValidator
from src.strategy.cli_builder import CLI_PROVIDER_ALIASES, CLI_PROVIDERS, CliBuilder

from .chat_content import chat_content_text

EMPTY_FRAME = pd.DataFrame()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SHANGHAI_TZ = timezone(timedelta(hours=8))
LOG = get_logger("frontend.services")
_DAILY_UI_CACHE: dict[str, tuple[str, str, Any]] = {}
_DAILY_UI_CACHE_LOCK = RLock()


def switch_ui_market(value: Any) -> str:
    """Switch the process-wide market and drop same-day UI caches."""

    market = set_current_market(value)
    with _DAILY_UI_CACHE_LOCK:
        _DAILY_UI_CACHE.clear()
    return market


KB_DELETE_CONFIRM_TOKEN = "DELETE"
LIVE_VALIDATION_PARAM_KEY = "_live_validation"
LIVE_BROKER_EVENT_CHOICES = [
    ("心跳", "heartbeat"),
    ("异常冻结", "error"),
]
STRATEGY_EXAMPLE_DIR = PROJECT_ROOT / "egs" / "examples" / "strategy_examples"
LEARNING_FILES = [
    PROJECT_ROOT / "README.md",
    *sorted((PROJECT_ROOT / "docs" / "usage").glob("*.md")),
    *sorted((PROJECT_ROOT / "doc").glob("*.md")),
    PROJECT_ROOT / "docs" / "archive" / "gradio_frontend.md",
    PROJECT_ROOT / "docs" / "archive" / "implementation_audit.md",
    PROJECT_ROOT / "docs" / "archive" / "page_completeness_audit.md",
    *sorted((PROJECT_ROOT / "docs" / "principles").glob("*.md")),
    *sorted((PROJECT_ROOT / "docs" / "reference").glob("*.md")),
    *sorted((PROJECT_ROOT / "docs" / "research").rglob("*.md")),
]

FONT_FAMILY = "Microsoft YaHei, Segoe UI, Arial, sans-serif"
COLORS = {
    "ink": "#111a20",
    "muted": "#60727b",
    "grid": "#d8e7eb",
    "positive": "#d94c62",
    "negative": "#0b9f8f",
    "strategy": "#0b8f86",
    "benchmark": "#c2892d",
    "blue": "#2f74d0",
    "violet": "#805ad5",
}
RELATION_TYPE_LABELS = {
    "industry": "行业",
    "concept": "概念",
    "index": "指数成分",
    "supply_chain": "产业链",
    "shareholder": "股东/机构",
    "news_cooccurrence": "新闻共现",
    "correlation": "收益相关",
    "task": "关联任务",
    "analysis": "分析构建",
    "relation": "其他关系",
}
RELATION_TYPE_COLORS = {
    "industry": COLORS["strategy"],
    "concept": COLORS["blue"],
    "index": "#0ea5b7",
    "supply_chain": COLORS["benchmark"],
    "shareholder": COLORS["violet"],
    "news_cooccurrence": "#b06744",
    "correlation": COLORS["positive"],
    "task": "#1d7fbe",
    "analysis": "#536dfe",
    "relation": "#7e9299",
}
RELATION_TYPE_CHOICES = [
    ("行业", "industry"),
    ("概念", "concept"),
    ("指数成分", "index"),
    ("产业链", "supply_chain"),
    ("股东/机构", "shareholder"),
    ("新闻共现", "news_cooccurrence"),
    ("收益相关", "correlation"),
    ("关联任务", "task"),
    ("分析构建", "analysis"),
]
CLI_TYPE_CHOICES = [(label, key) for key, label in CLI_PROVIDERS.items()]
AI_CONSOLE_GENERIC_BACKEND = "generic_agent"
AI_CONSOLE_BACKEND_CHOICES = [(row["label"], key) for key, row in composer_config()["backends"].items()]
AI_REASONING_CHOICES = [
    ("跟随后台", ""),
    ("低", "low"),
    ("中", "medium"),
    ("高", "high"),
    ("极高", "xhigh"),
]


def ai_console_model_choices() -> list[tuple[str, str]]:
    """Return safe, enabled model choices without exposing credentials."""
    rows = Repository().db.query(
        "SELECT id, name, model_name FROM llm_models WHERE enabled = 1 ORDER BY is_default DESC, id DESC"
    )
    choices: list[tuple[str, str]] = [("系统默认模型", "")]
    choices.extend(
        (
            f"{str(row.get('name') or row.get('model_name') or '模型')} · {str(row.get('model_name') or '')}",
            str(row.get("model_name") or ""),
        )
        for row in rows
    )
    return choices


BACKTEST_ENGINE_CHOICES = [
    ("跟随策略（自动）", "auto"),
    ("内置轻量回测", "simple"),
    ("组合目标权重引擎", "composition"),
    ("Qlib 投研引擎", "qlib"),
]
BACKTEST_ORDER_TYPE_CHOICES = [
    ("市价/收盘价", "market"),
    ("开盘价", "open"),
    ("限价", "limit"),
]
BACKTEST_PRICE_ADJUSTMENT_CHOICES = [
    ("前复权", "qfq"),
    ("后复权", "hfq"),
    ("不复权", "none"),
]
QLIB_RUN_TYPE_CHOICES = [
    ("Workflow", "workflow"),
    ("回测", "backtest"),
    ("因子", "factor"),
]
RECOMMEND_PLAN_CHOICES = [
    ("稳健低波", "defensive"),
    ("趋势动量", "momentum"),
    ("价值质量", "quality"),
    ("事件驱动", "event"),
    ("缠论结构", "chan"),
    ("均衡观察", "balanced"),
]
LEARNING_CATEGORY_CHOICES = [
    ("全部章节", "all"),
    ("使用文档", "usage"),
    ("原理文档", "principles"),
    ("快速上手", "readme"),
    ("正式设计", "design"),
    ("前端与体验", "frontend"),
    ("参考资料", "reference"),
    ("审计巡检", "audit"),
]
# 自定义仪表盘可勾选模块，顺序与 dashboard() 返回顺序（除状态条外）保持一致
DASHBOARD_MODULES: list[tuple[str, str, str]] = [
    ("kpis", "核心指标", "html"),
    ("monitor", "短线监控雷达", "table"),
    ("style", "市场风格", "table"),
    ("theme_chain", "题材主动链", "table"),
    ("paths", "下一交易段路径", "table"),
    ("actions", "待处理事项", "table"),
    ("risk", "账户分层与风险", "table"),
    ("holdings", "持仓股票与行情", "table"),
    ("account_plot", "账户净值", "plot"),
    ("strategy", "策略与任务状态", "table"),
    ("indices", "主要指数", "table"),
    ("watchlist", "自选行情", "table"),
    ("sector_plot", "板块强弱排名", "plot"),
]
DASHBOARD_MODULE_KEYS = [key for key, _, _ in DASHBOARD_MODULES]
DASHBOARD_MODULE_CHOICES = [(label, key) for key, label, _ in DASHBOARD_MODULES]
DASHBOARD_LAYOUT_FILE = PROJECT_ROOT / "data" / "dashboard_layout.json"
AI_WORKBENCH_PRESET_FILE = PROJECT_ROOT / "egs" / "config" / "platform" / "ai_workbench_presets.yaml"
QUANT_WORKFLOW_SOP_FILE = PROJECT_ROOT / "egs" / "config" / "platform" / "quant_workflow_sops.yaml"
LEARNING_CATEGORY_KEY_BY_LABEL = dict(LEARNING_CATEGORY_CHOICES)
INDEX_COLUMNS = ["code", "name", "price", "change", "change_pct", "volume", "amount", "data_source", "updated_at"]
WATCHLIST_COLUMNS = [
    "symbol",
    "name",
    "latest_price",
    "change_pct",
    "volume",
    "turnover_rate",
    "data_source",
    "updated_at",
    "group_id",
    "remark",
]
WATCHLIST_GROUP_COLUMNS = ["id", "name", "symbol_count", "sort_order", "created_at", "updated_at"]
SECTOR_COLUMNS = [
    "code",
    "name",
    "change_pct",
    "leader",
    "amount",
    "up_count",
    "down_count",
    "board",
    "data_source",
    "updated_at",
]
ACTION_COLUMNS = ["priority", "category", "item", "status", "next_step", "updated_at"]
MONITOR_COLUMNS = ["module", "signal", "status", "evidence", "updated_at"]
MARKET_STYLE_COLUMNS = ["dimension", "leader", "score", "evidence", "monitor_point"]
THEME_CHAIN_COLUMNS = ["chain_level", "name", "link_type", "evidence", "monitor_point"]
SCENARIO_COLUMNS = ["path", "condition", "validation", "risk_control"]
RISK_COLUMNS = ["metric", "value", "status", "note"]
HOLDING_COLUMNS = [
    "symbol",
    "name",
    "quantity",
    "available_qty",
    "latest_price",
    "change_pct",
    "market_value",
    "float_pnl",
    "float_pnl_pct",
    "data_source",
]
DASHBOARD_TRADE_COLUMNS = [
    "account_mode",
    "account_name",
    "symbol",
    "name",
    "direction",
    "price",
    "quantity",
    "fee",
    "status",
    "order_type",
    "traded_at",
    "source",
]
STRATEGY_DASHBOARD_COLUMNS = ["module", "name", "status", "key_metric", "updated_at", "next_step"]
STRATEGY_LIFECYCLE_COLUMNS = [
    "strategy_id",
    "name",
    "version",
    "stage",
    "status",
    "backtests",
    "latest_backtest",
    "latest_return",
    "paper_accounts",
    "live_configs",
    "next_step",
    "updated_at",
]
STRATEGY_VERSION_COMPARE_COLUMNS = [
    "策略ID",
    "版本",
    "状态",
    "接口类型",
    "来源",
    "最近回测",
    "总收益",
    "最大回撤",
    "夏普",
    "交易数",
    "默认参数",
    "更新时间",
    "备注",
]
STRATEGY_PARAM_SCHEMA_COLUMNS = ["参数名", "类型", "默认值", "说明"]
CLI_SESSION_COLUMNS = [
    "session_id",
    "cli_type",
    "cli_name",
    "status",
    "requirement",
    "artifact_count",
    "strategy_id",
    "error_msg",
    "created_at",
    "finished_at",
]
NEWS_COLUMNS = ["id", "category", "title", "source", "published_at", "sentiment", "keywords"]
RELATION_NODE_COLUMNS = [
    "id",
    "name",
    "group_label",
    "type",
    "layer",
    "parent_id",
    "path",
    "change_pct",
    "degree",
    "node_size",
]
RELATION_EDGE_COLUMNS = ["source", "target", "relation_type", "relation_label", "description", "weight"]
RELATION_PATH_COLUMNS = ["layer", "node_name", "path", "relations", "evidence"]
RELATION_ANALYSIS_COLUMNS = ["item", "conclusion", "evidence", "monitor"]
RESOURCE_POOL_COLUMNS = ["id", "name", "description", "source_type", "symbol_count", "total_weight", "updated_at"]
RESOURCE_POOL_ITEM_COLUMNS = [
    "id",
    "pool_id",
    "pool_name",
    "symbol",
    "name",
    "market",
    "weight",
    "tags",
    "remark",
    "source",
    "updated_at",
]
SECURITY_MASTER_COLUMNS = ["symbol", "market", "name", "abbr", "pinyin", "aliases", "exchange", "asset_type"]
AI_WORKSPACE_SESSION_COLUMNS = ["id", "project_name", "title", "session_type", "status", "updated_at"]
AI_WORKSPACE_NAV_COLUMNS = ["入口", "数量", "最近状态", "说明"]
AI_PROJECT_FILE_COLUMNS = ["类型", "路径", "说明"]
AI_PROJECT_TREE_LIMIT = 80
AI_PROJECT_IGNORED_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "data",
    "dist",
    "build",
}
AI_PROJECT_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".csv",
    ".env",
    ".example",
}
RECOMMEND_COLUMNS = [
    "rank",
    "symbol",
    "name",
    "score",
    "plan",
    "reason",
    "momentum",
    "liquidity",
    "sentiment",
    "chan",
    "selected_at",
]
RECOMMEND_DISPLAY_COLUMNS = {
    "rank": "排名",
    "symbol": "代码",
    "name": "名称",
    "score": "综合评分",
    "plan": "方案",
    "reason": "推荐理由",
    "momentum": "动量",
    "liquidity": "流动性",
    "sentiment": "情绪",
    "chan": "缠论",
    "selected_at": "入选时间",
}
RECOMMEND_COMPARE_COLUMNS = ["代码", "名称", "综合评分", "优势因子", "验证动作", "回测标的", "风险提示"]
RECOMMEND_TEMPLATE_COLUMNS = ["id", "name", "plan", "path", "limit_count", "universe_text", "updated_at"]
RECOMMEND_GROUP_SUMMARY_COLUMNS = [
    "方案",
    "路径",
    "候选数",
    "平均评分",
    "最高评分",
    "重合候选",
    "独有候选",
    "首位候选",
    "任务ID",
]
RECOMMEND_GROUP_SYMBOL_COLUMNS = [
    "代码",
    "名称",
    "出现组数",
    "覆盖方案",
    "平均评分",
    "最高评分",
    "最佳方案",
    "最佳排名",
    "建议动作",
]
RECOMMEND_COLUMN_ALIASES = {
    "rank": ("排名", "rank"),
    "symbol": ("代码", "symbol", "标的代码", "证券代码"),
    "name": ("名称", "name"),
    "score": ("综合评分", "score"),
    "plan": ("方案", "plan"),
    "reason": ("推荐理由", "reason"),
    "momentum": ("动量", "momentum"),
    "liquidity": ("流动性", "liquidity"),
    "sentiment": ("情绪", "sentiment"),
    "chan": ("缠论", "chan"),
}
RECOMMEND_FACTOR_LABELS = {
    "momentum": "动量",
    "liquidity": "流动性",
    "sentiment": "情绪",
    "chan": "缠论",
}
REPORT_COLUMNS = ["id", "title", "org", "analyst", "rating", "symbols", "publish_date", "summary", "link"]
PAPER_COLUMNS = [
    "id",
    "title",
    "authors",
    "source",
    "published_at",
    "abstract",
    "link",
    "is_favorite",
    "favorite_note",
]
LEARNING_COLUMNS = ["chapter_id", "category", "title", "path", "summary"]
POSITION_COLUMNS = [
    "symbol",
    "name",
    "quantity",
    "available_qty",
    "avg_cost",
    "latest_price",
    "market_value",
    "float_pnl",
    "float_pnl_pct",
]
ORDER_COLUMNS = [
    "order_id",
    "symbol",
    "direction",
    "order_type",
    "price",
    "quantity",
    "filled_qty",
    "avg_price",
    "status",
    "created_at",
]
LIVE_RUN_COLUMNS = [
    "run_id",
    "config_id",
    "name",
    "channel",
    "status",
    "started_at",
    "stopped_at",
    "heartbeat_at",
    "error_msg",
]
LIVE_BROKER_ADAPTER_COLUMNS = ["channel", "name", "available", "status", "event_types", "note"]
LIVE_RISK_COLUMNS = ["item", "value", "status", "note"]
LIVE_ALERT_COLUMNS = ["severity", "title", "message", "triggered_at"]
LIVE_LOG_COLUMNS = ["time", "level", "event", "detail"]
LIVE_DRY_RUN_ORDER_COLUMNS = [
    "代码",
    "名称",
    "方向",
    "订单类型",
    "计划价格",
    "计划数量",
    "计划金额",
    "目标权重",
    "风控状态",
    "说明",
]
LIVE_PRECHECK_COLUMNS = ["检查项", "当前值", "状态", "说明"]
TRADE_COLUMNS = [
    "symbol",
    "open_time",
    "open_price",
    "close_time",
    "close_price",
    "direction",
    "quantity",
    "order_type",
    "pnl",
    "pnl_pct",
    "commission",
    "holding_days",
    "fill_note",
    "signal",
]
BACKTEST_ATTRIBUTION_COLUMNS = ["section", "item", "value", "note"]
BACKTEST_COMPARE_COLUMNS = [
    "任务ID",
    "策略ID",
    "引擎",
    "标的",
    "区间",
    "初始资金",
    "总收益",
    "最大回撤",
    "夏普",
    "胜率",
    "交易数",
    "订单类型",
    "复权",
    "参数摘要",
]
BACKTEST_PARAM_COMPARE_COLUMNS = [
    "任务ID",
    "标的",
    "订单类型",
    "复权",
    "组合约束",
    "参数",
    "佣金率",
    "基准",
    "创建时间",
]
FACTOR_METRIC_COLUMNS = [
    "factor_key",
    "factor_name",
    "category",
    "rank_ic",
    "rank_ic_mean",
    "rank_ic_std",
    "ic",
    "icir",
    "hit_rate",
    "long_short_return",
    "coverage",
    "turnover",
    "avg_turnover_rate",
    "capacity_hint",
    "quantile_monotonicity",
    "sample_size",
    "status",
    "latest_date",
    "label_end",
    "snapshot_date",
    "asset_count",
    "factor_count",
]
FACTOR_ALERT_COLUMNS = ["severity", "factor_name", "title", "message", "triggered_at"]
FACTOR_SNAPSHOT_COLUMNS = [
    "factor_name",
    "symbol",
    "name",
    "rank",
    "quantile",
    "value",
    "change_pct",
    "turnover_rate",
]
QLIB_CONFIG_COLUMNS = ["item", "value", "note"]
QLIB_RUN_COLUMNS = [
    "run_id",
    "run_type",
    "status",
    "experiment_name",
    "market",
    "benchmark",
    "training_metric_summary",
    "portfolio_metric_summary",
    "artifact_count",
    "workflow_path",
    "provider_uri",
    "created_at",
    "error_msg",
]
SYSTEM_SETTING_COLUMNS = ["分组", "配置项", "键", "当前值", "来源", "环境变量", "重启生效", "说明"]
SYSTEM_STORAGE_COLUMNS = ["存储对象", "路径", "用途", "适配场景"]
SYSTEM_LAKE_COLUMNS = ["组件", "状态", "版本", "路径", "说明"]

METRIC_LABELS = {
    "benchmark_label": "比较基准",
    "total_return": "总收益率",
    "annual_return": "年化收益率",
    "max_drawdown": "最大回撤",
    "annual_volatility": "年化波动率",
    "calmar": "Calmar 比率",
    "daily_var_95": "日 VaR（95%）",
    "sharpe": "夏普比率",
    "sortino": "索提诺比率",
    "win_rate": "胜率",
    "win_count": "盈利笔数",
    "loss_count": "亏损笔数",
    "profit_loss_ratio": "盈亏比",
    "profit_factor": "Profit Factor",
    "average_win": "平均盈利",
    "average_loss": "平均亏损",
    "expectancy": "单笔期望收益",
    "best_trade": "最大单笔盈利",
    "worst_trade": "最大单笔亏损",
    "average_holding_days": "平均持仓天数",
    "trade_count": "交易次数",
    "excess_return": "超额收益",
    "commission_paid": "佣金支出",
    "tax_paid": "交易税支出",
    "transfer_fee_paid": "过户费支出",
    "other_fee_paid": "其他规费支出",
    "slippage_cost": "滑点成本归因",
    "total_execution_cost": "实际执行总成本",
    "net_pnl": "成本后净损益",
    "gross_pnl_before_costs": "加回成本损益",
    "net_return": "成本后净收益率",
    "gross_return_before_costs": "加回成本收益率",
    "unfilled_order_count": "未完全成交次数",
    "cost_breakdown_complete": "成本拆分完整性",
    "turnover_ratio": "累计换手率",
    "average_exposure": "平均持仓暴露",
    "max_exposure": "最大持仓暴露",
    "max_drawdown_duration_days": "最大回撤持续天数",
    "max_drawdown_recovery_days": "最大回撤恢复天数",
    "result_scope": "结果范围",
    "curve_available": "逐日曲线",
    "order_type": "订单类型",
    "price_adjustment": "复权方式",
    "max_position_count": "最大持仓数",
    "max_position_weight": "单票最大权重",
    "lot_size": "最小成交数量（股/份）",
    "data_source": "数据源",
    "engine_mode": "引擎模式",
}

BACKTEST_METRIC_EXPLANATIONS = {
    "total_return": "区间内策略净值相对初始资金的累计变化。",
    "annual_return": "按 252 个交易日年化的区间收益，短样本仅作参考。",
    "max_drawdown": "从历史峰值到后续谷值的最大跌幅，越接近 0 越好。",
    "annual_volatility": "日收益波动率年化，反映净值波动强度。",
    "calmar": "年化收益除以最大回撤绝对值，用于比较收益与回撤代价。",
    "daily_var_95": "历史日收益的 5% 分位数，表示较差交易日的风险水平。",
    "sharpe": "日收益均值与波动率之比再年化，当前未扣除无风险利率。",
    "sortino": "只用下行波动计算的风险调整收益。",
    "win_rate": "盈利交易笔数占已平仓交易笔数的比例。",
    "profit_loss_ratio": "平均盈利金额除以平均亏损绝对值，不等同于 Profit Factor。",
    "profit_factor": "总盈利除以总亏损绝对值，衡量整体盈亏质量。",
    "expectancy": "每笔已平仓交易的平均净收益。",
    "turnover_ratio": "成交金额总和除以初始资金，粗略反映换手强度。",
    "average_exposure": "每日持仓市值占组合总资产的平均比例。",
    "max_exposure": "回测期间持仓市值占总资产的最高比例。",
    "max_drawdown_duration_days": "最长处于历史峰值以下的日历天数。",
    "max_drawdown_recovery_days": "最大回撤从峰值到恢复峰值所需的日历天数。",
    "commission_paid": "新任务为全部实际外部成交佣金，包含未平仓买入；旧任务保留原统计。",
    "slippage_cost": "成交价相对参考价的差额归因，已进入净值，不再次扣减。",
    "total_execution_cost": "佣金、税费和滑点归因之和；内部调拨不重复计费。",
    "gross_return_before_costs": "保持实际成交不变，加回成本后的收益归因，并非另跑零成本策略。",
    "net_return": "现金、持仓市值及已扣交易费用组成的净资产收益。",
    "unfilled_order_count": "含资金、结算、限价、状态与流动性导致的拒绝、延后及部分成交。",
}

RECOMMEND_PLAN_DESCRIPTIONS = {
    "defensive": "偏向低波动、现金流稳定和风险暴露可控，适合先做观察池。",
    "momentum": "偏向价格强度、成交活跃和趋势延续，适合短中期动量研究。",
    "quality": "偏向基本面质量、估值约束和盈利稳定性，适合中长期候选池。",
    "event": "偏向新闻、研报、产业催化和事件共振，适合主题跟踪。",
    "chan": "偏向缠论结构、8 道门控信号和 K 线位置，适合结构交易候选池。",
    "balanced": "综合趋势、质量、流动性和情绪，适合默认筛选。",
}

AI_EXPERT_COLUMNS = ["expert_id", "name", "group", "focus", "starter", "deliverable", "task_type"]
AI_TEAM_COLUMNS = ["team_id", "name", "group", "lead", "members", "summary", "starter", "deliverable"]
AI_JOB_TEMPLATE_COLUMNS = ["template_id", "label", "job_type", "cron", "enabled", "params"]
QUANT_WORKFLOW_STEP_COLUMNS = ["step_order", "title", "status", "goal", "evidence"]
QUANT_WORKFLOW_INSIGHT_COLUMNS = ["insight_type", "title", "conclusion", "evidence", "severity", "confidence"]
QUANT_WORKFLOW_QUESTION_COLUMNS = ["question", "answer", "evidence"]
QUANT_WORKFLOW_ADVICE_COLUMNS = ["priority", "action", "rationale", "next_step", "guardrail"]
QUANT_WORKFLOW_ARTIFACT_COLUMNS = ["artifact_type", "title", "ref_type", "ref_id", "summary"]
QUANT_WORKFLOW_RUN_COLUMNS = ["run_id", "mode", "sop_id", "title", "status", "summary", "created_at"]


@lru_cache(maxsize=1)
def _ai_workbench_config() -> dict[str, Any]:
    """Load AI workbench presets from YAML so prompts stay out of source code."""
    payload = yaml.safe_load(AI_WORKBENCH_PRESET_FILE.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("AI 工作台预设配置必须是 YAML 对象")
    return payload


def _preset_items(section: str) -> list[dict[str, Any]]:
    items = _ai_workbench_config().get(section) or []
    return [dict(item) for item in items if isinstance(item, dict)]


def _choice_pairs(section: str) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for item in _preset_items(section):
        value = str(item.get("id") or "").strip()
        label = str(item.get("label") or item.get("name") or value).strip()
        if value and label:
            choices.append((label, value))
    return choices


def _preset_by_id(section: str, value: Any) -> dict[str, Any]:
    selected = str(value or "").strip()
    items = _preset_items(section)
    for item in items:
        if str(item.get("id") or "") == selected:
            return item
    return items[0] if items else {}


def _choice_label(choices: Sequence[tuple[str, str]], value: Any) -> str:
    selected = str(value or "")
    for label, candidate in choices:
        if candidate == selected:
            return label
    return selected or "-"


@lru_cache(maxsize=1)
def _quant_workflow_config() -> dict[str, Any]:
    """Load quant workflow SOP presets from YAML."""
    payload = yaml.safe_load(QUANT_WORKFLOW_SOP_FILE.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("量化闭环 SOP 配置必须是 YAML 对象")
    return payload


def _workflow_items(section: str) -> list[dict[str, Any]]:
    items = _quant_workflow_config().get(section) or []
    return [dict(item) for item in items if isinstance(item, dict)]


def _workflow_choice_pairs(section: str) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for item in _workflow_items(section):
        value = str(item.get("id") or "").strip()
        label = str(item.get("label") or item.get("name") or value).strip()
        if value and label:
            choices.append((label, value))
    return choices


def _workflow_sop_choices() -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for item in _workflow_items("sops"):
        value = str(item.get("id") or "").strip()
        label = str(item.get("name") or value).strip()
        if value and label:
            choices.append((label, value))
    return choices


ACCOUNT_MODE_CHOICES = _choice_pairs("account_modes")
AI_TASK_TYPE_CHOICES = _choice_pairs("task_types")
AI_EXPERT_GROUP_CHOICES = _choice_pairs("expert_groups")
AI_EXPERT_CHOICES = [(str(item.get("name")), str(item.get("id"))) for item in _preset_items("experts")]
AI_TEAM_CHOICES = [(str(item.get("name")), str(item.get("id"))) for item in _preset_items("team_presets")]
AI_JOB_TEMPLATE_CHOICES = [
    (str(item.get("label") or item.get("name")), str(item.get("id"))) for item in _preset_items("job_templates")
]
QUANT_WORKFLOW_MODE_CHOICES = _workflow_choice_pairs("workflow_modes")
QUANT_WORKFLOW_SOP_CHOICES = _workflow_sop_choices()
STRATEGY_PARAM_TYPE_CHOICES = [
    ("整数 int", "int"),
    ("小数 float", "float"),
    ("布尔 bool", "bool"),
    ("字符串 str", "str"),
    ("JSON 对象/数组", "json"),
]


def strategy_example_choices() -> list[tuple[str, str]]:
    """Return egs strategy files as Gradio dropdown choices."""
    if not STRATEGY_EXAMPLE_DIR.exists():
        return []
    return [
        (f"{path.stem} - {path.name}", path.relative_to(PROJECT_ROOT).as_posix())
        for path in sorted(STRATEGY_EXAMPLE_DIR.glob("*.py"))
    ]


def _schema_defaults(schema: Any) -> dict[str, Any]:
    if isinstance(schema, dict):
        return dict(schema)
    if isinstance(schema, list):
        return {
            str(item["name"]): item.get("default") for item in schema if isinstance(item, dict) and item.get("name")
        }
    return {}


def _category_for_learning_file(path: Path) -> str:
    path_text = path.relative_to(PROJECT_ROOT).as_posix()
    if path_text.startswith("docs/usage/"):
        return "使用文档"
    if path_text.startswith("docs/principles/"):
        return "原理文档"
    if path.name == "README.md":
        return "快速上手"
    if path_text.startswith("doc/"):
        return "正式设计"
    if "reference/" in path_text or "research/" in path_text:
        return "参考资料"
    if "audit" in path_text or path.name.endswith("_audit.md"):
        return "审计巡检"
    return "前端与体验"


@lru_cache(maxsize=1)
def _learning_entries() -> list[dict[str, Any]]:
    """Scan learning documents once; chapter_id stays stable per file order."""
    entries: list[dict[str, Any]] = []
    chapter_id = 0
    for path in LEARNING_FILES:
        if not path.exists() or path.name.startswith("tasks"):
            continue
        chapter_id += 1
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8-sig")
        category_label = _category_for_learning_file(path)
        title, summary = _markdown_title_and_summary(content, path.stem)
        entries.append(
            {
                "chapter_id": chapter_id,
                "category": category_label,
                "category_key": LEARNING_CATEGORY_KEY_BY_LABEL.get(category_label, "frontend"),
                "title": title,
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "summary": summary,
            }
        )
    return entries


def _markdown_title_and_summary(text: str, fallback: str) -> tuple[str, str]:
    title = fallback
    summary = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") and title == fallback:
            title = line.lstrip("#").strip() or fallback
            continue
        if not line.startswith("|") and not line.startswith("-") and not line.startswith("#"):
            summary = line[:160]
            break
    return title, summary or "章节内容见详情。"


def _markdown_link(url: Any, label: str = "打开链接") -> str:
    text = str(url or "").strip()
    if not text:
        return "-"
    return f"[{label}]({text})"


def _local_now() -> datetime:
    return datetime.now(SHANGHAI_TZ).replace(microsecond=0)


def _display_now() -> str:
    return _local_now().strftime("%Y-%m-%d %H:%M:%S")


def _today_key() -> str:
    return _local_now().date().isoformat()


def _cache_key(parts: Sequence[Any]) -> str:
    settings = get_settings()
    namespace = [str(settings.db_path), str(settings.data_dir), str(settings.data_mode), current_market()]
    return json.dumps([*namespace, *(str(part) for part in parts)], ensure_ascii=False, sort_keys=True)


def _daily_cached(
    key_parts: Sequence[Any], loader: Callable[[], Any], force_refresh: bool = False
) -> tuple[Any, bool, str]:
    """Cache low-frequency UI payloads for the current local trading day."""
    cache_key = _cache_key(key_parts)
    today = _today_key()
    with _DAILY_UI_CACHE_LOCK:
        cached = _DAILY_UI_CACHE.get(cache_key)
        if cached and cached[0] == today and not force_refresh:
            return copy.deepcopy(cached[2]), True, cached[1]

    value = loader()
    refreshed_at = _display_now()
    with _DAILY_UI_CACHE_LOCK:
        _DAILY_UI_CACHE[cache_key] = (today, refreshed_at, copy.deepcopy(value))
    return copy.deepcopy(value), False, refreshed_at


def _cache_badge(cache_hit: bool, refreshed_at: str) -> str:
    state = "今日缓存命中" if cache_hit else "已刷新"
    return f"最后刷新 `{refreshed_at}`  ·  {state}"


def parse_json(value: Any, label: str = "JSON", default: Any = None) -> Any:
    """Parse an optional JSON field and return a useful validation error."""
    if value is None or value == "":
        return {} if default is None else default
    if isinstance(value, dict | list):
        return value
    try:
        return json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} 格式错误：第 {exc.lineno} 行第 {exc.colno} 列") from exc


def parse_csv(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).replace("，", ",").split(",") if item.strip()]


def _strategy_param_value(value: Any, value_type: str) -> Any:
    text = str(value or "").strip()
    normalized_type = str(value_type or "str").strip().lower()
    if normalized_type == "int":
        return int(float(text or 0))
    if normalized_type == "float":
        return float(text or 0)
    if normalized_type == "bool":
        if text.lower() in {"1", "true", "yes", "y", "on", "是", "真"}:
            return True
        if text.lower() in {"0", "false", "no", "n", "off", "否", "假", ""}:
            return False
        raise ValueError("布尔默认值请填写 true/false、1/0 或 是/否")
    if normalized_type == "json":
        return parse_json(text or "{}", "JSON 默认值")
    return text


def _strategy_param_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, dict | list):
        return "json"
    return "str"


def _strategy_param_rows(params: dict[str, Any], descriptions: dict[str, str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in params.items():
        rows.append(
            {
                "参数名": name,
                "类型": _strategy_param_type(value),
                "默认值": json.dumps(value, ensure_ascii=False) if isinstance(value, dict | list) else value,
                "说明": (descriptions or {}).get(name, ""),
            }
        )
    return rows


def parse_stock_symbols(value: Any) -> list[str]:
    return parse_security_symbols(value)


def resolve_stock_symbol(value: Any, field_name: str = "股票代码/名称") -> str:
    symbol = (parse_stock_symbols(value) or [""])[0]
    if not symbol:
        raise ValueError(f"请输入有效的{field_name}")
    return symbol


def _table_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, pd.DataFrame):
        return value.to_dict("records")
    if isinstance(value, dict):
        headers = value.get("headers") or value.get("columns") or []
        data = value.get("data") or value.get("values") or []
        if headers and data:
            return pd.DataFrame(data, columns=headers).to_dict("records")
        if "items" in value and isinstance(value["items"], list):
            return _table_records(value["items"])
        return [value]
    if isinstance(value, list):
        if not value:
            return []
        if all(isinstance(item, dict) for item in value):
            return [dict(item) for item in value]
        return pd.DataFrame(value).to_dict("records")
    return []


def _recommend_cell(row: dict[str, Any], key: str, default: Any = "") -> Any:
    for column in RECOMMEND_COLUMN_ALIASES.get(key, (key,)):
        if column in row and row[column] not in (None, ""):
            return row[column]
    return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _recommend_records(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in _table_records(value):
        symbol = str(_recommend_cell(raw, "symbol")).strip()
        if not re.fullmatch(r"\d{6}", symbol):
            continue
        rows.append(
            {
                "rank": _recommend_cell(raw, "rank", len(rows) + 1),
                "symbol": symbol,
                "name": str(_recommend_cell(raw, "name", symbol)).strip() or symbol,
                "score": _safe_float(_recommend_cell(raw, "score")),
                "plan": str(_recommend_cell(raw, "plan")).strip(),
                "reason": str(_recommend_cell(raw, "reason")).strip(),
                "momentum": _safe_float(_recommend_cell(raw, "momentum")),
                "liquidity": _safe_float(_recommend_cell(raw, "liquidity")),
                "sentiment": _safe_float(_recommend_cell(raw, "sentiment")),
                "chan": _safe_float(_recommend_cell(raw, "chan")),
            }
        )
    return rows


def require_id(value: Any, label: str) -> int:
    try:
        result = int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"请输入有效的{label}") from exc
    if result <= 0:
        raise ValueError(f"{label}必须大于 0")
    return result


def _optional_id(value: Any) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    return require_id(value, "ID")


def require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label}不能为空")
    return text


def uploaded_file_path(value: Any) -> Path:
    if not value:
        raise ValueError("请选择上传文件")
    if isinstance(value, str | Path):
        path = Path(value)
    elif isinstance(value, dict):
        path = Path(str(value.get("path") or value.get("name") or ""))
    else:
        path = Path(str(getattr(value, "path", "") or getattr(value, "name", "")))
    if not path.exists() or not path.is_file():
        raise ValueError("上传文件不存在或不可读取")
    return path


def _ordered_steps(steps: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, step in enumerate(steps, start=1):
        row = dict(step)
        row["step_order"] = index
        rows.append(row)
    return rows


def _normalize_account_mode(value: Any) -> str:
    allowed = {choice_value for _, choice_value in ACCOUNT_MODE_CHOICES}
    selected = str(value or "paper").strip()
    return selected if selected in allowed else "paper"


def _normalize_ai_task_type(value: Any) -> str:
    allowed = {choice_value for _, choice_value in AI_TASK_TYPE_CHOICES}
    selected = str(value or "general").strip()
    return selected if selected in allowed else "general"


def _chat_history_messages(history: list[dict[str, Any]] | list[list[str | None]] | None) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for item in list(history or [])[-20:]:
        if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
            messages.append({"role": str(item["role"]), "content": chat_content_text(item.get("content"))})
            continue
        if isinstance(item, list | tuple) and len(item) == 2:
            if item[0]:
                messages.append({"role": "user", "content": chat_content_text(item[0])})
            if item[1]:
                messages.append({"role": "assistant", "content": chat_content_text(item[1])})
    return messages


def to_frame(value: Any, columns: Sequence[str] | None = None) -> pd.DataFrame:
    """Convert service payloads to stable, readable Gradio tables."""
    if value is None:
        return pd.DataFrame(columns=list(columns or []))
    if isinstance(value, dict) and "items" in value:
        value = value.get("items") or []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        value = [value]
    if not value:
        if columns:
            return pd.DataFrame(columns=list(columns))
        return pd.DataFrame([{"状态": "暂无数据"}])
    rows: list[dict[str, Any]] = []
    for item in value:
        row = dict(item) if isinstance(item, dict) else {"value": item}
        for key, cell in list(row.items()):
            if isinstance(cell, dict | list | tuple):
                row[key] = json.dumps(cell, ensure_ascii=False)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if columns:
        for column in columns:
            if column not in frame:
                frame[column] = None
        frame = frame[list(columns)]
    return frame


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _blend_rgb(start: tuple[int, int, int], end: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    red = round(start[0] + (end[0] - start[0]) * ratio)
    green = round(start[1] + (end[1] - start[1]) * ratio)
    blue = round(start[2] + (end[2] - start[2]) * ratio)
    return red, green, blue


def _gradient_cell_style(value: Any, lower: float, upper: float, center: float) -> str:
    if pd.isna(value) or upper <= lower:
        return ""
    ratio = (float(value) - lower) / (upper - lower)
    center_ratio = (center - lower) / (upper - lower)
    neutral = (255, 255, 255)
    positive = (187, 247, 208)
    negative = (254, 202, 202)
    if ratio >= center_ratio:
        denom = max(1.0 - center_ratio, 1e-9)
        color = _blend_rgb(neutral, positive, (ratio - center_ratio) / denom)
    else:
        denom = max(center_ratio, 1e-9)
        color = _blend_rgb(neutral, negative, (center_ratio - ratio) / denom)
    return f"background-color: rgb({color[0]}, {color[1]}, {color[2]}); color: #111827;"


def styled_frame(
    value: Any,
    columns: Sequence[str] | None = None,
    gradient: Sequence[str] | None = None,
    cmap: str = "RdYlGn",
    symmetric: bool = True,
    center: float = 0.0,
) -> Any:
    """Build a Gradio table and optionally attach color-scale styling.

    ``gradient`` lists numeric columns that receive a background gradient.
    ``symmetric`` keeps diverging colormaps centered on zero so positive and
    negative values compare fairly (e.g. daily change percentages).
    The style is implemented with plain CSS to avoid pulling in matplotlib for
    pandas ``Styler.background_gradient`` during Gradio serialization.
    """

    frame = value if isinstance(value, pd.DataFrame) else to_frame(value, columns)
    if not gradient or not isinstance(frame, pd.DataFrame) or frame.empty:
        return frame
    numeric = frame.copy()
    for column in gradient:
        if column in numeric.columns:
            numeric[column] = pd.to_numeric(numeric[column], errors="coerce")
    gradient_columns = [column for column in gradient if column in numeric.columns and numeric[column].notna().any()]
    if not gradient_columns:
        return frame
    styler = numeric.style
    for column in gradient_columns:
        series = numeric[column].dropna()
        if series.empty:
            continue
        if symmetric:
            bound = float(series.abs().max())
            lower = center - bound if bound > 0 else float(series.min())
            upper = center + bound if bound > 0 else float(series.max())
        else:
            lower = float(series.min())
            upper = float(series.max())
        styler = styler.map(
            lambda cell, min_value=lower, max_value=upper: _gradient_cell_style(cell, min_value, max_value, center),
            subset=[column],
        )
    styler.format(na_rep="")
    return styler


def _compact_mapping(value: dict[str, Any], limit: int = 4) -> str:
    if not value:
        return ""
    items = list(value.items())[:limit]
    suffix = "；..." if len(value) > limit else ""
    return "；".join(f"{key}={val}" for key, val in items) + suffix


def _calendar_range_text(calendar: dict[str, Any]) -> str:
    start = str(calendar.get("range_start") or "").strip()
    end = str(calendar.get("range_end") or "").strip()
    if start and end:
        return f"{start} 至 {end}"
    if start:
        return f"{start} 起"
    if end:
        return f"截至 {end}"
    return "未记录"


def ui_error_message(exc: Exception) -> str:
    return _public_ui_error_message(exc)
