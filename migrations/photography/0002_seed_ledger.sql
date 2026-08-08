CREATE TABLE photography_seed_runs (
  seed_id TEXT PRIMARY KEY,
  photo_count INTEGER NOT NULL CHECK (photo_count > 0),
  applied_at TEXT NOT NULL
);
