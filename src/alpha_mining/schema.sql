CREATE TABLE IF NOT EXISTS alpha_datasets (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, kind TEXT NOT NULL,
 payload TEXT NOT NULL, digest TEXT NOT NULL, provenance TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alpha_studies (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, mode TEXT NOT NULL,
 dataset_id INTEGER NOT NULL REFERENCES alpha_datasets(id), config TEXT NOT NULL,
 digest TEXT NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alpha_candidates (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id INTEGER NOT NULL REFERENCES alpha_studies(id),
 origin TEXT NOT NULL, hypothesis TEXT NOT NULL, implementation TEXT NOT NULL,
 digest TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alpha_trials (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id INTEGER NOT NULL REFERENCES alpha_studies(id),
 candidate_id INTEGER, split TEXT NOT NULL, status TEXT NOT NULL,
 evidence TEXT NOT NULL, created_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS alpha_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id INTEGER NOT NULL REFERENCES alpha_studies(id),
 kind TEXT NOT NULL, payload TEXT NOT NULL, previous_digest TEXT NOT NULL,
 digest TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alpha_reviews (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id INTEGER NOT NULL REFERENCES alpha_studies(id),
 candidate_id INTEGER REFERENCES alpha_candidates(id), track TEXT NOT NULL,
 decision TEXT NOT NULL, reviewer TEXT NOT NULL, evidence TEXT NOT NULL,
 candidate_digest TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alpha_holdouts (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id INTEGER NOT NULL UNIQUE REFERENCES alpha_studies(id),
 candidate_id INTEGER NOT NULL REFERENCES alpha_candidates(id), market TEXT NOT NULL,
 symbols TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alpha_events_study ON alpha_events(study_id,id);
CREATE INDEX IF NOT EXISTS idx_alpha_candidates_study ON alpha_candidates(study_id,id);
CREATE INDEX IF NOT EXISTS idx_alpha_trials_study ON alpha_trials(study_id,id);
