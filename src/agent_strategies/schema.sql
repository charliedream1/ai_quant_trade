CREATE TABLE IF NOT EXISTS agent_strategy_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, recipe TEXT NOT NULL, status TEXT NOT NULL,
 request TEXT NOT NULL, config TEXT NOT NULL, evidence TEXT NOT NULL, result TEXT NOT NULL,
 digest TEXT NOT NULL, lineage TEXT NOT NULL, as_of TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_strategy_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL REFERENCES agent_strategy_runs(id),
 kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_strategy_scores (
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL REFERENCES agent_strategy_runs(id),
 lineage TEXT NOT NULL, actor TEXT NOT NULL, channel TEXT NOT NULL, value REAL NOT NULL,
 effective_at TEXT NOT NULL, evidence TEXT NOT NULL,
 UNIQUE(run_id, actor, channel)
);
CREATE INDEX IF NOT EXISTS idx_agent_strategy_events ON agent_strategy_events(run_id,id);
CREATE INDEX IF NOT EXISTS idx_agent_strategy_scores ON agent_strategy_scores(lineage,channel,effective_at);
