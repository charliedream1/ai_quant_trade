"""One local inbox, lightweight synchronization and checked assistant assets."""

from threading import RLock
from time import monotonic
from urllib.parse import quote

from loguru import logger

from src.agent.image_validation import validate_images
from src.core.config import PROJECT_ROOT, get_settings

from .config import config
from .sources import synchronize, task
from .store import NotificationStore

SYNC: dict[str, tuple[float, list[str]]] = {}
LOCK = RLock()


class NotificationService:
    def __init__(self, repo=None):
        self.store = NotificationStore(repo)

    def feed(self, client_id, after=0, before=0, initial=False):
        cfg = config()
        key = str(self.store.db.db_path)
        with LOCK:
            stamp, warnings = SYNC.get(key, (0.0, []))
            if cfg["enabled"] and monotonic() - stamp >= cfg["sync_seconds"]:
                warnings = synchronize(self.store)
                SYNC[key] = monotonic(), warnings
        result = self.store.feed(client_id, after, before, initial)
        return {**result, "warnings": warnings}


def report_saved(report: dict) -> None:
    """A best-effort terminal report hook cannot change report state or fail its save."""
    try:
        if not config()["enabled"]:
            return
        task(
            NotificationService().store,
            "report",
            report["run_id"],
            report["status"],
            report.get("updated_at") or report["created_at"],
        )
    except Exception as exc:
        logger.warning("报告提醒未写入 | error_type={}", type(exc).__name__)


def public_config() -> dict:
    cfg = config()
    avatar = cfg["avatar"]
    images = {"robot": "/static/" + avatar["robot"], "icon": "/static/" + avatar["icon"]}
    if avatar["custom_image"]:
        try:
            root = PROJECT_ROOT / "src/frontend/assets"
            path = (root / avatar["custom_image"]).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or path.suffix.lower() not in {".png", ".jpg", ".webp"}
                or path.stat().st_size > avatar["max_bytes"]
            ):
                raise ValueError("自定义助手素材不合法")
            validate_images([(path.name, path.read_bytes())])
            images["custom"] = "/static/" + quote(path.relative_to(root).as_posix())
        except Exception as exc:
            logger.warning("助手素材校验失败，使用内置形象 | error_type={}", type(exc).__name__)
    return {
        key: cfg[key]
        for key in ("enabled", "poll_seconds", "backoff_seconds", "toast_limit", "toast_width", "toast_seconds", "ui")
    } | {
        "api": get_settings().api_prefix + "/notifications",
        "avatar": {"style": avatar["style"] if avatar["style"] in images else "robot", "images": images},
    }
