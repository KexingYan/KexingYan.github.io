PRAGMA foreign_keys = ON;

CREATE TABLE photo_series (
  id TEXT PRIMARY KEY,
  number_label TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE photos (
  id TEXT PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  series_id TEXT NOT NULL REFERENCES photo_series(id),
  date_taken TEXT,
  date_published TEXT,
  location_display TEXT NOT NULL DEFAULT '',
  caption TEXT NOT NULL DEFAULT '',
  alt TEXT NOT NULL,
  camera TEXT,
  lens TEXT,
  focal_length TEXT,
  aperture TEXT,
  shutter_speed TEXT,
  iso INTEGER,
  orientation TEXT NOT NULL CHECK (orientation IN ('portrait', 'landscape')),
  layout_hint TEXT NOT NULL CHECK (
    layout_hint IN ('hero', 'wide', 'landscape', 'portrait-left', 'portrait-right', 'pair-left', 'pair-right', 'panorama', 'standard')
  ),
  featured INTEGER NOT NULL DEFAULT 0 CHECK (featured IN (0, 1)),
  allow_download INTEGER NOT NULL DEFAULT 1 CHECK (allow_download IN (0, 1)),
  sort_order INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  asset_version INTEGER NOT NULL DEFAULT 1 CHECK (asset_version >= 1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE photo_asset_versions (
  photo_id TEXT NOT NULL REFERENCES photos(id),
  asset_version INTEGER NOT NULL CHECK (asset_version >= 1),
  master_object_key TEXT NOT NULL UNIQUE,
  source_filename TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  original_width INTEGER NOT NULL CHECK (original_width > 0),
  original_height INTEGER NOT NULL CHECK (original_height > 0),
  source_bytes INTEGER NOT NULL CHECK (source_bytes > 0),
  processing_state TEXT NOT NULL CHECK (
    processing_state IN ('accepted', 'awaiting-local-processing', 'processing', 'ready', 'failed', 'superseded')
  ),
  processing_error TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (photo_id, asset_version)
);

CREATE TABLE photo_publish_revisions (
  revision TEXT PRIMARY KEY,
  manifest_object_key TEXT NOT NULL UNIQUE,
  photo_count INTEGER NOT NULL CHECK (photo_count >= 0),
  created_by_sub TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX photos_series_order_idx ON photos(series_id, status, sort_order);
CREATE INDEX photos_status_updated_idx ON photos(status, updated_at);
CREATE INDEX photo_asset_processing_idx ON photo_asset_versions(processing_state, created_at);
