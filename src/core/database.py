"""SQLite database manager and schema bootstrap."""

import sqlite3
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, ClassVar

from .config import get_settings
from .file_lock import file_lock
from .logger import get_logger
from .migrations import apply_migrations


class Database:
    _instance_lock = RLock()
    _instance: ClassVar["Database | None"] = None
    _conn: sqlite3.Connection | None
    _initialized: bool
    SCHEMA_SQL = Path(__file__).with_name("database_schema.sql").read_text(encoding="utf-8")

    def __new__(cls, db_path: Path | None = None) -> "Database":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._conn = None
            return cls._instance

    def __init__(self, db_path: Path | None = None) -> None:
        with self._instance_lock:
            if self._initialized:
                return
            target = Path(db_path or get_settings().db_path)
            with file_lock(target):
                try:
                    self._initialize(target)
                except BaseException:
                    self.close()
                    raise

    def _initialize(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path or settings.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._transaction_depth = 0
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(self.SCHEMA_SQL)
        self._conn = conn
        apply_migrations(self)
        self.logger = get_logger("database")
        migrated_secrets = self._migrate_legacy_llm_secrets()
        if migrated_secrets:
            self.logger.info("Migrated {} legacy LLM secret(s) to .llm_env", migrated_secrets)
        self.logger.info("Database initialized: {}", self.db_path)
        self._initialized = True

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        conn = self._connection()
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _migrate_legacy_llm_secrets(self) -> int:
        from .env_file import default_key_name, save_env_value

        conn = self._connection()
        rows = conn.execute("SELECT id, name, api_key, api_key_env FROM llm_models WHERE api_key <> ''").fetchall()
        for row in rows:
            env_name = row["api_key_env"] or default_key_name(row["name"])
            save_env_value(env_name, row["api_key"])
            conn.execute("UPDATE llm_models SET api_key = '', api_key_env = ? WHERE id = ?", (env_name, row["id"]))
        if rows:
            conn.commit()
        return len(rows)

    @classmethod
    def reset_instance(cls) -> None:
        if cls._instance is not None:
            cls._instance.close()
        cls._instance = None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            conn = self._connection()
            cursor = conn.execute(sql, tuple(params))
            if not self._transaction_depth:
                conn.commit()
            return cursor

    def executemany(self, sql: str, items: Iterable[Sequence[Any]]) -> None:
        with self._lock:
            conn = self._connection()
            conn.executemany(sql, items)
            if not self._transaction_depth:
                conn.commit()

    @contextmanager
    def transaction(self):
        """Serialize a complete batch; nested failures roll back their savepoint."""
        with self._lock:
            conn = self._connection()
            name = f"application_batch_{self._transaction_depth}"
            conn.execute(f"SAVEPOINT {name}")
            self._transaction_depth += 1
            try:
                yield
            except BaseException:
                conn.execute(f"ROLLBACK TO {name}")
                raise
            finally:
                conn.execute(f"RELEASE {name}")
                self._transaction_depth -= 1

    def executescript(self, sql: str) -> None:
        with self._lock:
            conn = self._connection()
            conn.executescript(sql)
            conn.commit()

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection().execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection().execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        row = self.query_one(sql, params)
        if not row:
            return None
        return next(iter(row.values()))

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database connection is closed")
        return self._conn
