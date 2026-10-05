CREATE TABLE IF NOT EXISTS kiosk_releases (
 id BIGSERIAL PRIMARY KEY,
 version VARCHAR(80) NOT NULL UNIQUE,
 source_url TEXT NOT NULL,
 download_url TEXT NOT NULL DEFAULT '',
 notes TEXT NOT NULL DEFAULT '',
 active BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS kiosk_releases_one_active ON kiosk_releases(active) WHERE active;
