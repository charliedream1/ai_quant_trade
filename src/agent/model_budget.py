"""One deadline and cancellation signal for quota waits, retries and network attempts."""

import time
from dataclasses import dataclass, field
from threading import Event

from src.core.exceptions import BusinessError, ErrorCode
from src.core.llm_config import llm_config
from src.core.stream_control import stream_cancelled


@dataclass
class CallBudget:
    seconds: float
    started: float = field(default_factory=time.monotonic)

    def remaining(self) -> float:
        if stream_cancelled():
            raise BusinessError(ErrorCode.LLM_ERROR, "模型调用已取消")
        remaining = self.seconds - (time.monotonic() - self.started)
        if remaining <= 0:
            raise BusinessError(ErrorCode.LLM_ERROR, "模型调用整体超时")
        return remaining

    def wait(self, seconds: float) -> None:
        end = time.monotonic() + max(0, seconds)
        while end > time.monotonic():
            remaining = self.remaining()
            Event().wait(min(end - time.monotonic(), remaining, llm_config()["rate_limit"]["poll_seconds"]))
        self.remaining()
