"""Small typed boundary independent of execution-engine imports."""

from _thread import LockType
from dataclasses import dataclass, field
from threading import Lock

COMPONENTS = {"cn_analysis", "cn_debate", "contest_data", "contest_research"}


@dataclass(frozen=True)
class ShadowPermit:
    weights: dict[str, float]


@dataclass
class CallBudget:
    limit: int
    used: int = 0
    lock: LockType = field(default_factory=Lock, repr=False)

    def take(self):
        with self.lock:
            if self.used >= self.limit:
                raise ValueError("达到整轮组合研究的实际模型请求上限")
            self.used += 1
