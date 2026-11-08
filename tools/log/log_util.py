"""Compatibility exports; maintained implementation lives in its source domain."""

from src.core.operation_logging import addlog, init_log, log, time_str

__all__ = ["addlog", "init_log", "log", "time_str"]
