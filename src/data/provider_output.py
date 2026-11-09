"""Capture a Python SDK call's own prints without replacing process-global stdout."""

from functools import lru_cache
from types import FunctionType
from typing import Any

import yaml

from src.core.config import PROJECT_ROOT
from src.core.logger import get_logger

log = get_logger("data.provider")


@lru_cache(maxsize=1)
def output_policy() -> dict[str, Any]:
    return yaml.safe_load((PROJECT_ROOT / "egs/config/data/provider_logging.yaml").read_text(encoding="utf-8"))


def provider_call(operation, *args, **kwargs):
    """Use a per-call globals copy; keep the SDK module and other threads untouched."""
    policy = output_policy()

    def sdk_output(*values, sep=" ", end="\n", **options):
        message = sep.join(str(value) for value in values).strip()
        if not message:
            return
        success = message.casefold() in policy["successful_auth_messages"]
        level = policy["successful_auth_level"] if success else policy["other_stdout_level"]
        log.log(level, "provider output | {}", message[: policy["max_message_chars"]])

    if isinstance(operation, FunctionType):
        wrapped = FunctionType(
            operation.__code__,
            {**operation.__globals__, "print": sdk_output},
            operation.__name__,
            operation.__defaults__,
            operation.__closure__,
        )
        wrapped.__kwdefaults__ = operation.__kwdefaults__
        return wrapped(*args, **kwargs)
    return operation(*args, **kwargs)
