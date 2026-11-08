"""Compatibility exports; maintained implementation lives in its source domain."""

from src.core.calendar_utils import is_festival, is_holidays, is_workdays

__all__ = ["is_workdays", "is_holidays", "is_festival"]
