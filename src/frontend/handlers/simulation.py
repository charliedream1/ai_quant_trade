"""Simulation callback boundary."""

from .base import DomainHandler


class SimulationHandler(DomainHandler):
    domain = "simulation"
    allowed_methods = frozenset(
        {
            "backtest_analysis",
            "backtest_detail",
            "backtest_engines",
            "backtest_param_snapshot",
            "backtest_resolved_parameters",
            "backtest_to_paper_account",
            "backtests",
            "compare_backtests",
            "create_backtest",
            "create_paper_account",
            "delete_backtest",
            "empty_backtest_analysis",
            "execution_cost_preview",
            "export_backtest_trades",
            "paper_cancel",
            "paper_match_orders",
            "paper_order",
            "paper_overview",
            "parameter_profiles",
            "preview_strategy_parameters",
            "quant_workflow_create_run",
            "quant_workflow_runs",
            "quant_workflow_snapshot",
        }
    )
