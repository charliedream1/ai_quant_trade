"""Dashboard callback boundary."""

from .base import DomainHandler


class DashboardHandler(DomainHandler):
    domain = "dashboard"
    allowed_methods = frozenset(
        {
            "home_account",
            "home_market",
            "home_operations",
            "home_news",
            "dashboard_account",
            "dashboard_market",
            "dashboard_strategy",
            "dashboard_summary",
            "dashboard_trade_history",
            "load_dashboard_layout",
            "save_dashboard_layout",
        }
    )
