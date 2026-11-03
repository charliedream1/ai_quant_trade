CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, source_key TEXT NOT NULL,
 fingerprint TEXT NOT NULL UNIQUE, signature TEXT NOT NULL, severity TEXT NOT NULL,
 title TEXT NOT NULL, message TEXT NOT NULL, target TEXT NOT NULL,
 occurred_at TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS notification_source ON notifications(source, source_key, id);
CREATE INDEX IF NOT EXISTS notification_date ON notifications(created_at, id);
CREATE TABLE IF NOT EXISTS notification_states (
 client_id TEXT NOT NULL, notification_id INTEGER NOT NULL REFERENCES notifications(id),
 read_at TEXT, dismissed_at TEXT, PRIMARY KEY(client_id, notification_id)
);
