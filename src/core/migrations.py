"""Versioned, idempotent upgrades separated from database connection ownership."""

from src.core.timeutil import utc_now_iso
from src.knowledge.config import knowledge_config


def apply_migrations(database):
    conn = database._connection()
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL)")
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=2").fetchone():
        default = str(knowledge_config()["default_library"]).replace("'", "''")
        database._ensure_columns(
            "kb_documents",
            {
                "library_name": f"TEXT NOT NULL DEFAULT '{default}'",
                "attachment_session": "TEXT NOT NULL DEFAULT ''",
                "chunk_chars": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        database._ensure_columns("kb_qa_history", {"library_name": f"TEXT NOT NULL DEFAULT '{default}'"})
        conn.execute("INSERT OR IGNORE INTO schema_migrations VALUES(?,?)", (2, utc_now_iso()))
        conn.commit()
    if conn.execute("SELECT 1 FROM schema_migrations WHERE version=1").fetchone():
        return
    database._ensure_columns(
        "llm_models",
        {
            "api_key_env": "TEXT NOT NULL DEFAULT ''",
            "temperature": "REAL NOT NULL DEFAULT 0.2",
            "max_tokens": "INTEGER NOT NULL DEFAULT 1200",
            "timeout_seconds": "REAL NOT NULL DEFAULT 60",
            "system_prompt": "TEXT NOT NULL DEFAULT ''",
            "call_count": "INTEGER NOT NULL DEFAULT 0",
            "success_count": "INTEGER NOT NULL DEFAULT 0",
            "failure_count": "INTEGER NOT NULL DEFAULT 0",
            "total_duration_ms": "INTEGER NOT NULL DEFAULT 0",
            "last_duration_ms": "INTEGER",
            "last_called_at": "TEXT",
            "last_status": "TEXT NOT NULL DEFAULT ''",
            "last_error": "TEXT NOT NULL DEFAULT ''",
        },
    )
    database._ensure_columns("backtest_tasks", {"engine": "TEXT NOT NULL DEFAULT 'simple'"})
    database._ensure_columns("factor_alerts", {"scope": "TEXT NOT NULL DEFAULT ''"})
    database._ensure_columns("kb_qa_history", {"session_id": "TEXT NOT NULL DEFAULT 'default'"})
    database._ensure_columns("kb_documents", {"original_file_id": "TEXT NOT NULL DEFAULT ''"})
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_tasks_engine ON backtest_tasks(engine, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_qa_history_session ON kb_qa_history(session_id, id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kb_qa_sessions_updated ON kb_qa_sessions(updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resource_pool_items_pool ON resource_pool_items(pool_id, symbol)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resource_pools_updated ON resource_pools(updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_workspace_sessions_updated ON ai_workspace_sessions(updated_at)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ai_workspace_messages_session ON ai_workspace_messages(session_id, id)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recommend_templates_updated ON recommend_templates(updated_at)")
    conn.commit()
    conn.execute("INSERT OR IGNORE INTO schema_migrations VALUES(?,?)", (1, utc_now_iso()))
    conn.commit()
