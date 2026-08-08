PRAGMA foreign_keys = ON;

CREATE TABLE photography_admin_state (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  collection_revision INTEGER NOT NULL DEFAULT 1 CHECK (collection_revision >= 1),
  updated_at TEXT NOT NULL
);

INSERT INTO photography_admin_state (singleton, collection_revision, updated_at)
VALUES (1, 1, '2026-08-07T00:00:00Z');

CREATE TABLE photo_drafts (
  photo_id TEXT PRIMARY KEY REFERENCES photos(id),
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  base_updated_at TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
  updated_by_sub TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE photo_asset_derivatives (
  photo_id TEXT NOT NULL,
  asset_version INTEGER NOT NULL,
  variant TEXT NOT NULL CHECK (variant IN ('thumbnail', 'preview', 'display', 'download')),
  object_key TEXT NOT NULL UNIQUE,
  width INTEGER NOT NULL CHECK (width > 0),
  height INTEGER NOT NULL CHECK (height > 0),
  bytes INTEGER NOT NULL CHECK (bytes > 0),
  etag TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (photo_id, asset_version, variant),
  FOREIGN KEY (photo_id, asset_version)
    REFERENCES photo_asset_versions(photo_id, asset_version)
);

CREATE INDEX photo_drafts_updated_idx ON photo_drafts(updated_at);
CREATE INDEX photo_derivatives_version_idx
  ON photo_asset_derivatives(photo_id, asset_version);
