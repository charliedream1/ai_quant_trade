"""Deduplicated event history; closing a card never changes its business source."""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from src.core.repository import Repository
from src.core.timeutil import utc_now_iso

from .config import config


def signature(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class NotificationStore:
    def __init__(self, repo=None):
        self.repo = repo or Repository()
        self.db = self.repo.db
        self.db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))

    def publish(self, source, source_key, severity, title, message, destination, occurred_at=None) -> dict:
        stamp = utc_now_iso()
        content = signature([severity, title, message, destination])
        with self.db.transaction():
            previous = self.db.query_one(
                "SELECT * FROM notifications WHERE source=? AND source_key=? ORDER BY id DESC LIMIT 1",
                (source, str(source_key)),
            )
            if previous and previous["signature"] == content and not previous["resolved_at"]:
                return previous
            if previous and not previous["resolved_at"]:
                self.repo.update("notifications", previous["id"], {"resolved_at": stamp})
            return self.repo.insert(
                "notifications",
                {
                    "source": source,
                    "source_key": str(source_key),
                    "signature": content,
                    "fingerprint": signature([source, str(source_key), content, previous["id"] if previous else 0]),
                    "severity": severity,
                    "title": title,
                    "message": message,
                    "target": json.dumps(destination, ensure_ascii=False),
                    "occurred_at": occurred_at or stamp,
                    "created_at": stamp,
                },
            )

    def resolve(self, source, key):
        self.db.execute(
            "UPDATE notifications SET resolved_at=? WHERE source=? AND source_key=? AND resolved_at IS NULL",
            (utc_now_iso(), source, str(key)),
        )

    def action(self, client_id: str, identifier: int, action: str):
        self.repo.get("notifications", identifier)
        if action not in {"read", "dismiss"}:
            raise ValueError("未知提醒操作")
        statement = (
            "INSERT INTO notification_states(client_id,notification_id,read_at) VALUES(?,?,?) "
            "ON CONFLICT(client_id,notification_id) DO UPDATE SET read_at=excluded.read_at"
            if action == "read"
            else "INSERT INTO notification_states(client_id,notification_id,dismissed_at) VALUES(?,?,?) "
            "ON CONFLICT(client_id,notification_id) DO UPDATE SET dismissed_at=excluded.dismissed_at"
        )
        self.db.execute(
            statement,
            (client_id, identifier, utc_now_iso()),
        )

    def read_all(self, client_id: str):
        cutoff = (datetime.now(UTC) - timedelta(days=config()["retention_days"])).isoformat()
        self.db.execute(
            """INSERT INTO notification_states(client_id,notification_id,read_at)
            SELECT ?,id,? FROM notifications WHERE created_at>=? OR (severity='critical' AND resolved_at IS NULL)
            ON CONFLICT(client_id,notification_id) DO UPDATE SET read_at=excluded.read_at""",
            (client_id, utc_now_iso(), cutoff),
        )

    def feed(self, client_id: str, after: int = 0, before: int = 0, initial=False) -> dict:
        cfg = config()
        cutoff = (datetime.now(UTC) - timedelta(days=cfg["retention_days"])).isoformat()
        joined = """SELECT n.*,s.read_at,s.dismissed_at FROM notifications n
            LEFT JOIN notification_states s ON s.notification_id=n.id AND s.client_id=?
            WHERE (n.created_at>=? OR (n.severity='critical' AND n.resolved_at IS NULL))"""
        items = self.db.query(
            joined + (" AND n.id<?" if before else "") + " ORDER BY n.id DESC LIMIT ?",
            [client_id, cutoff, *([before] if before else []), cfg["page_size"]],
        )
        events = self.db.query(
            joined + " AND n.id>? ORDER BY n.id LIMIT ?", (client_id, cutoff, after, cfg["max_page_size"])
        )
        critical = self.db.query(
            joined + " AND n.severity='critical' AND n.resolved_at IS NULL ORDER BY n.id DESC LIMIT ?",
            (client_id, cutoff, cfg["page_size"]),
        )
        for row in [*items, *events, *critical]:
            row["target"] = json.loads(row["target"])
        unread = self.db.scalar(
            """SELECT COUNT(*) FROM notifications n LEFT JOIN notification_states s
            ON s.notification_id=n.id AND s.client_id=? WHERE (n.created_at>=? OR (n.severity='critical' AND n.resolved_at IS NULL)) AND s.read_at IS NULL""",
            (client_id, cutoff),
        )
        latest = self.db.scalar("SELECT COALESCE(MAX(id),0) FROM notifications")
        return {
            "items": items,
            "events": [] if initial else events,
            "critical": critical,
            "unread": unread,
            "cursor": latest if initial else events[-1]["id"] if events else after,
            "has_more_events": not initial and len(events) == cfg["max_page_size"],
            "before": items[-1]["id"] if len(items) == cfg["page_size"] else 0,
        }
