"""Business exception and error code definitions."""

from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    MISSING_PARAM = 1001
    INVALID_PARAM = 1002
    PARSE_ERROR = 1003
    NOT_FOUND = 1004
    NON_EMPTY_RESOURCE = 1005
    RESOURCE_REFERENCED = 1006
    CONSTRAINT_CONFLICT = 1007
    DATA_SOURCE_ERROR = 2001
    NEWS_SOURCE_ERROR = 2002
    DOCUMENT_SOURCE_ERROR = 2003
    LLM_ERROR = 2004
    MCP_ERROR = 2005
    CLI_ERROR = 2006
    STRATEGY_STATE_ERROR = 3001
    TASK_NOT_FINISHED = 3002
    STRATEGY_INVALID = 3003
    BACKTEST_RUNNING_DELETE = 3004
    ORDER_STATE_ERROR = 3005
    PAPER_ORDER_REJECTED = 3006
    LIVE_STATE_ERROR = 4001
    LIVE_CONFIG_LOCKED = 4002
    LIVE_PRECHECK_FAILED = 4003
    RISK_PARAM_LOCKED = 4004
    RISK_REJECTED = 4005
    DATABASE_ERROR = 5001
    CONFIG_DEPENDENCY = 5002
    STORAGE_ERROR = 5003
    UNKNOWN = 5999


class BusinessError(Exception):
    def __init__(self, code: int, message: str, data=None) -> None:
        super().__init__(message)
        self.code = int(code)
        self.message = message
        self.data = data


def not_found(resource: str = "资源") -> BusinessError:
    return BusinessError(ErrorCode.NOT_FOUND, f"{resource}不存在")
