"""System routes."""

import platform
import sys
import time
from pathlib import Path

from fastapi import APIRouter

from src.api.route_guards import ValidatedRoute
from src.api.schemas.common import ok
from src.api.ws_hub import ws_hub
from src.core.config import get_settings
from src.core.database import Database
from src.data import DataSourceManager
from src.scheduler import scheduler_runtime
from src.scheduler.calendar_updater import trading_calendar_alerts, trading_calendar_status

router = APIRouter(tags=["通用系统"], route_class=ValidatedRoute)
START_TS = time.time()
PYTHON_VERSION = sys.version.split()[0]
OS_INFO = platform.platform()
_SIZE_CACHE = {"ts": 0.0, "value": 0}


@router.get("/system/capabilities")
def capabilities():
    manager = DataSourceManager()
    return ok(
        {
            "version": get_settings().version,
            "data_mode": manager.mode,
            "market": manager.market,
            "data_source": manager.source_name,
            "is_mock": manager.is_mock,
            "cli_builder": "simulator",
            "ai_backends": {
                "generic": "requires_model",
                "codex": "requires_local_cli",
                "trae": "unavailable",
                "workbuddy": "unavailable",
            },
        }
    )


@router.get("/health")
def health():
    db = Database()
    writable = True
    try:
        db.execute("SELECT 1")
    except Exception:
        writable = False
    calendar = trading_calendar_status()
    return ok(
        {
            "status": "ok" if writable else "degraded",
            "database": {"writable": writable},
            "scheduler": scheduler_runtime.status(),
            "trading_calendar": calendar,
            "system_alerts": trading_calendar_alerts(status=calendar),
            "data_sources": DataSourceManager().health(),
        }
    )


@router.get("/system/info")
def system_info():
    settings = get_settings()
    size = _fast_data_dir_size(Path(settings.data_dir), Path(settings.db_path))
    return ok(
        {
            "version": settings.version,
            "build_time": "development",
            "started_at": START_TS,
            "uptime_seconds": int(time.time() - START_TS),
            "python": PYTHON_VERSION,
            "os": OS_INFO,
            "data_dir_size": size,
            "websocket_clients": ws_hub.client_count,
        }
    )


def _fast_data_dir_size(data_dir: Path, db_path: Path) -> int:
    now = time.time()
    if now - float(_SIZE_CACHE["ts"]) < 30:
        return int(_SIZE_CACHE["value"])

    try:
        size = db_path.stat().st_size if db_path.exists() else 0
    except OSError:
        size = 0
    _SIZE_CACHE["ts"] = now
    _SIZE_CACHE["value"] = size
    return size
