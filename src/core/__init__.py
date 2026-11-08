"""Core infrastructure exports."""

from .config import Settings, get_settings
from .exceptions import BusinessError, ErrorCode
from .logger import get_logger, setup_logging

__all__ = [
    "BusinessError",
    "Database",
    "ErrorCode",
    "MarketDataLake",
    "Settings",
    "get_logger",
    "get_settings",
    "setup_logging",
]


def __getattr__(name):
    if name == "Database":
        from .database import Database

        return Database
    # A lightweight environment check must not require the optional data-lake stack.
    if name == "MarketDataLake":
        from .market_lake import MarketDataLake

        return MarketDataLake
    raise AttributeError(name)
