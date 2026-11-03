from datetime import datetime
from typing import Any

class CronTrigger:
    @classmethod
    def from_crontab(cls, expr: str, timezone: Any = ...) -> CronTrigger: ...
    def get_next_fire_time(self, previous_fire_time: datetime | None, now: datetime) -> datetime | None: ...
