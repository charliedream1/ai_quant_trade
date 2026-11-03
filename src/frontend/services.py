"""Backward-compatible facade for modular frontend services.

Domain callback implementations live in :mod:`src.frontend.service`.  This
module intentionally preserves the established import path used by pages,
tests, and extensions.
"""

from __future__ import annotations

from .service.admin import AdminServiceMixin
from .service.ai import AIServiceMixin
from .service.alpha import AlphaUIMixin
from .service.assistant import AssistantServiceMixin
from .service.dashboard import DashboardServiceMixin
from .service.etf import ETFServiceMixin
from .service.execution_costs import ExecutionCostsMixin
from .service.foundation import (
    _DAILY_UI_CACHE,
    ACCOUNT_MODE_CHOICES,
    AI_CONSOLE_BACKEND_CHOICES,
    AI_EXPERT_CHOICES,
    AI_EXPERT_GROUP_CHOICES,
    AI_JOB_TEMPLATE_CHOICES,
    AI_REASONING_CHOICES,
    AI_TASK_TYPE_CHOICES,
    AI_TEAM_CHOICES,
    BACKTEST_ENGINE_CHOICES,
    BACKTEST_ORDER_TYPE_CHOICES,
    BACKTEST_PRICE_ADJUSTMENT_CHOICES,
    CLI_TYPE_CHOICES,
    DASHBOARD_MODULE_CHOICES,
    DASHBOARD_MODULE_KEYS,
    DASHBOARD_MODULES,
    LIVE_BROKER_EVENT_CHOICES,
    QLIB_RUN_TYPE_CHOICES,
    QUANT_WORKFLOW_MODE_CHOICES,
    QUANT_WORKFLOW_SOP_CHOICES,
    RECOMMEND_PLAN_CHOICES,
    RELATION_TYPE_CHOICES,
    STRATEGY_PARAM_TYPE_CHOICES,
    current_market,
    strategy_example_choices,
    styled_frame,
    switch_ui_market,
    ui_error_message,
)
from .service.knowledge import KnowledgeServiceMixin
from .service.live import LiveServiceMixin
from .service.market import MarketServiceMixin
from .service.monitoring import MonitoringUIMixin
from .service.parameters import ParameterServiceMixin
from .service.report_library import ReportLibraryMixin
from .service.research import ResearchServiceMixin
from .service.resource_import_ui import ResourceImportUIMixin
from .service.simulation import SimulationServiceMixin
from .service.strategy import StrategyServiceMixin
from .service.visuals import (
    model_stat_figure,
    paper_distribution_figure,
    report_rating_figure,
    strategy_stat_figure,
)


class FrontendService(
    AlphaUIMixin,
    ReportLibraryMixin,
    ExecutionCostsMixin,
    MonitoringUIMixin,
    ResourceImportUIMixin,
    DashboardServiceMixin,
    MarketServiceMixin,
    ResearchServiceMixin,
    StrategyServiceMixin,
    SimulationServiceMixin,
    ParameterServiceMixin,
    ETFServiceMixin,
    LiveServiceMixin,
    KnowledgeServiceMixin,
    AIServiceMixin,
    AdminServiceMixin,
    AssistantServiceMixin,
):
    """Aggregate all domain callbacks for legacy and modular Gradio apps."""

    frontend_callback_service = True

    def callback(self, name: str):
        return getattr(self, name)


__all__ = [
    "FrontendService",
    "ACCOUNT_MODE_CHOICES",
    "AI_CONSOLE_BACKEND_CHOICES",
    "AI_REASONING_CHOICES",
    "AI_EXPERT_CHOICES",
    "AI_EXPERT_GROUP_CHOICES",
    "AI_JOB_TEMPLATE_CHOICES",
    "AI_TASK_TYPE_CHOICES",
    "AI_TEAM_CHOICES",
    "BACKTEST_ENGINE_CHOICES",
    "BACKTEST_ORDER_TYPE_CHOICES",
    "BACKTEST_PRICE_ADJUSTMENT_CHOICES",
    "CLI_TYPE_CHOICES",
    "DASHBOARD_MODULE_CHOICES",
    "DASHBOARD_MODULE_KEYS",
    "DASHBOARD_MODULES",
    "LIVE_BROKER_EVENT_CHOICES",
    "QLIB_RUN_TYPE_CHOICES",
    "QUANT_WORKFLOW_MODE_CHOICES",
    "QUANT_WORKFLOW_SOP_CHOICES",
    "RECOMMEND_PLAN_CHOICES",
    "RELATION_TYPE_CHOICES",
    "STRATEGY_PARAM_TYPE_CHOICES",
    "_DAILY_UI_CACHE",
    "current_market",
    "model_stat_figure",
    "paper_distribution_figure",
    "report_rating_figure",
    "strategy_example_choices",
    "strategy_stat_figure",
    "styled_frame",
    "switch_ui_market",
    "ui_error_message",
]
