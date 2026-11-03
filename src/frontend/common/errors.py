"""Public callback errors do not expose arbitrary internal exception messages."""

from src.core.exceptions import BusinessError
from src.core.redaction import redact_text


def ui_error_message(exc: Exception) -> str:
    if isinstance(exc, BusinessError):
        return f"[{exc.code}] {redact_text(exc.message)}"
    if isinstance(exc, ValueError):
        return redact_text(str(exc))
    return "操作未完成，请使用运行标识查看服务日志"
