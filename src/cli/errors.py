"""CLI errors and process status independent of HTTP 200."""

from enum import IntEnum
from typing import Any


class ExitCode(IntEnum):
    OK = 0
    INPUT = 2
    TRANSPORT = 3
    TIMEOUT = 4
    BUSINESS = 5
    UNAVAILABLE = 6
    CONDITION = 7
    INTERRUPTED = 130


class CliError(Exception):
    def __init__(
        self, message: str, exit_code: int = ExitCode.INPUT, *, envelope: dict[str, Any] | None = None, **meta: Any
    ) -> None:
        super().__init__(message)
        self.exit_code = int(exit_code)
        self.envelope = envelope or {"code": None, "message": message, "data": None}
        self.meta = {"error_origin": "client", "error_type": type(self).__name__, **meta}


def result_exit(result: dict[str, Any], *, execution: bool = False, fail_on_verdict: str = "") -> int:
    if result.get("code") != 0:
        return ExitCode.UNAVAILABLE if result.get("code") == 5002 else ExitCode.BUSINESS
    data = result.get("data")
    if not isinstance(data, dict):
        return ExitCode.OK
    status = str(data.get("status") or "").lower()
    if execution and (data.get("success") is False or data.get("isError") is True):
        return ExitCode.BUSINESS
    if execution and status in {"blocked", "unavailable", "missing", "mock-disabled", "disabled"}:
        return ExitCode.UNAVAILABLE
    if execution and status in {"failed", "error", "timeout", "rejected", "失败", "错误", "超时"}:
        return ExitCode.BUSINESS
    if fail_on_verdict and data.get("verdict") in fail_on_verdict.split(","):
        return ExitCode.CONDITION
    return ExitCode.OK
