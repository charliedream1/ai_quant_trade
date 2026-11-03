"""Live trading callback boundary."""

from .base import DomainHandler


class LiveHandler(DomainHandler):
    domain = "live"
    allowed_methods = frozenset(
        {
            "create_live_config",
            "live_broker_adapters",
            "live_broker_event",
            "live_configs",
            "live_dry_run_plan",
            "live_mark_error",
            "live_monitor",
            "live_pause",
            "live_precheck_start",
            "live_resume",
            "live_risk_summary",
            "live_runs",
            "live_start",
            "live_status",
            "live_stop",
            "live_validation_summary",
            "update_live_risk",
        }
    )
