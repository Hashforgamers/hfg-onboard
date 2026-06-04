CREATE TABLE IF NOT EXISTS game_console_catalog (
    id BIGSERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    console_catalog_id INTEGER NOT NULL REFERENCES console_catalog(id) ON DELETE CASCADE,
    source_platform VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    popularity_score NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_game_console_catalog_game_catalog UNIQUE (game_id, console_catalog_id)
);

CREATE INDEX IF NOT EXISTS ix_game_console_catalog_catalog_active_score
    ON game_console_catalog (console_catalog_id, is_active, popularity_score DESC, game_id);

CREATE INDEX IF NOT EXISTS ix_game_console_catalog_game_active
    ON game_console_catalog (game_id, is_active);

CREATE INDEX IF NOT EXISTS ix_games_name_trgm_fallback
    ON games (LOWER(name));

INSERT INTO game_console_catalog (game_id, console_catalog_id, source_platform)
SELECT DISTINCT
    g.id,
    cc.id,
    g.platform
FROM games g
JOIN console_catalog cc
  ON cc.slug = CASE
    WHEN LOWER(g.platform) IN ('pc', 'linux', 'macos', 'web', 'classic macintosh') THEN 'pc'
    WHEN LOWER(g.platform) IN ('playstation 5', 'playstation 4', 'playstation 3', 'playstation 2', 'ps vita') THEN 'playstation'
    WHEN LOWER(g.platform) IN ('xbox', 'xbox one', 'xbox 360', 'xbox series s/x') THEN 'xbox'
    WHEN LOWER(g.platform) = 'nintendo switch' THEN 'nintendo_switch'
    ELSE NULL
  END
WHERE g.platform IS NOT NULL
  AND cc.is_active = true
ON CONFLICT (game_id, console_catalog_id) DO UPDATE
SET source_platform = EXCLUDED.source_platform,
    is_active = true,
    updated_at = NOW();

CREATE TABLE IF NOT EXISTS game_discovery_events (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER,
    session_id VARCHAR(128),
    game_id INTEGER REFERENCES games(id) ON DELETE SET NULL,
    game_name VARCHAR(255),
    console_catalog_id INTEGER REFERENCES console_catalog(id) ON DELETE SET NULL,
    console_slug VARCHAR(100),
    city VARCHAR(100),
    pincode VARCHAR(10),
    lat NUMERIC(9, 6),
    lng NUMERIC(9, 6),
    event_type VARCHAR(32) NOT NULL,
    search_query VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_game_discovery_event_type
        CHECK (event_type IN ('view', 'click', 'search', 'result_view', 'booking_start', 'booking_success'))
);

CREATE INDEX IF NOT EXISTS ix_game_discovery_events_recent_game
    ON game_discovery_events (game_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_game_discovery_events_catalog_city_recent
    ON game_discovery_events (console_catalog_id, city, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_game_discovery_events_type_recent
    ON game_discovery_events (event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS game_popularity_rankings (
    id BIGSERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    console_catalog_id INTEGER NOT NULL REFERENCES console_catalog(id) ON DELETE CASCADE,
    city VARCHAR(100) NOT NULL DEFAULT '',
    score_24h NUMERIC(14, 2) NOT NULL DEFAULT 0,
    score_7d NUMERIC(14, 2) NOT NULL DEFAULT 0,
    clicks_count INTEGER NOT NULL DEFAULT 0,
    searches_count INTEGER NOT NULL DEFAULT 0,
    result_views_count INTEGER NOT NULL DEFAULT 0,
    bookings_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_game_popularity_rankings_scope UNIQUE (game_id, console_catalog_id, city)
);

CREATE INDEX IF NOT EXISTS ix_game_popularity_rankings_scope_score
    ON game_popularity_rankings (console_catalog_id, city, score_7d DESC, score_24h DESC);
