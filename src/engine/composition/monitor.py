"""Explicitly enabled paper risk monitoring, independent from research jobs."""

from threading import Event, Thread

from loguru import logger

from src.core.task_control import TaskLease
from src.strategy.composition.accounts import PipelineAccounts
from src.strategy.composition.config import config
from src.strategy.composition.service import PipelineService, today


class PaperRiskMonitor:
    def __init__(self):
        self.stopped = Event()
        self.thread: Thread | None = None
        self.lease = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stopped.clear()
        self.thread = Thread(target=self._loop, daemon=True, name="pipeline-paper-risk")
        self.thread.start()

    def tick(self):
        for account in PipelineAccounts().list():
            if self.stopped.is_set():
                return
            state = account["state"]
            if not state.get("monitor_enabled"):
                continue
            request = {
                **state["monitor_request"],
                "mode": "paper",
                "agent_mode": "off",
                "risk_only": True,
                "account_id": account["id"],
                "end_date": today(),
                "refresh_decision": False,
            }
            try:
                PipelineService().start(request)
            except Exception as exc:
                logger.warning("paper risk monitor | account={} error={}", account["id"], exc)

    def _loop(self):
        while not self.stopped.is_set():
            try:
                if self.lease is None:
                    self.lease = TaskLease("leader", "paper-risk-monitor")
                self.tick()
            except ValueError:
                pass
            except Exception as exc:
                logger.warning("paper risk monitor unavailable | error={}", exc)
            self.stopped.wait(config()["defaults"]["monitor_seconds"])

    def stop(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=5)
        if self.lease and (not self.thread or not self.thread.is_alive()):
            self.lease.close()
            self.lease = None
