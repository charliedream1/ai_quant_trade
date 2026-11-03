CREATE TABLE IF NOT EXISTS strategy_pipelines (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, definition TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategy_pipeline_versions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, pipeline_id INTEGER NOT NULL REFERENCES strategy_pipelines(id),
 version INTEGER NOT NULL, definition TEXT NOT NULL, compiled TEXT NOT NULL, digest TEXT NOT NULL,
 manifest TEXT NOT NULL, strategy_id INTEGER, created_at TEXT NOT NULL, UNIQUE(pipeline_id,version)
);
CREATE TABLE IF NOT EXISTS strategy_pipeline_runs (
 id TEXT PRIMARY KEY, version_id INTEGER NOT NULL REFERENCES strategy_pipeline_versions(id),
 status TEXT NOT NULL, request TEXT NOT NULL, result TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS strategy_pipeline_accounts (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, version_id INTEGER NOT NULL REFERENCES strategy_pipeline_versions(id),
 state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0, last_as_of TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_strategy_pipeline_runs_version ON strategy_pipeline_runs(version_id,created_at);
