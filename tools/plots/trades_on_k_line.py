"""Compatibility exports; maintained implementation lives in its source domain."""

from src.visualization.trade_charts import plot_trades_on_capital, plot_trades_on_k_line, show_plt

__all__ = ["plot_trades_on_capital", "plot_trades_on_k_line", "show_plt"]
