-- Schema version 1. Repeatable creation, not an automatic migration system.
SET TIME ZONE 'UTC';
CREATE SCHEMA IF NOT EXISTS arcadia;
SET search_path TO arcadia, public;
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    channel TEXT NOT NULL CHECK (channel IN ('paid_social','paid_search','creator')),
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL CHECK (ends_on >= starts_on)
);
CREATE TABLE IF NOT EXISTS campaign_daily_spend (
    campaign_id INTEGER NOT NULL REFERENCES campaigns,
    spend_date DATE NOT NULL,
    spend_usd NUMERIC(12,2) NOT NULL CHECK (spend_usd >= 0),
    impressions INTEGER NOT NULL CHECK (impressions >= 0),
    clicks INTEGER NOT NULL CHECK (clicks BETWEEN 0 AND impressions),
    PRIMARY KEY (campaign_id, spend_date)
);
CREATE TABLE IF NOT EXISTS game_releases (
    release_id INTEGER PRIMARY KEY,
    version TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('ios','android')),
    released_at TIMESTAMPTZ NOT NULL,
    UNIQUE (version, platform)
);
CREATE TABLE IF NOT EXISTS levels (
    level_id INTEGER PRIMARY KEY CHECK (level_id > 0),
    name TEXT NOT NULL,
    chapter INTEGER NOT NULL CHECK (chapter > 0)
);
CREATE TABLE IF NOT EXISTS level_configurations (
    level_id INTEGER NOT NULL REFERENCES levels,
    release_id INTEGER NOT NULL REFERENCES game_releases,
    difficulty NUMERIC(5,3) NOT NULL CHECK (difficulty > 0),
    time_limit_seconds INTEGER NOT NULL CHECK (time_limit_seconds > 0),
    PRIMARY KEY (level_id, release_id)
);
CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('currency','booster','cosmetic')),
    base_price_usd NUMERIC(10,2) NOT NULL CHECK (base_price_usd > 0)
);
CREATE TABLE IF NOT EXISTS exchange_rates (
    rate_date DATE NOT NULL,
    currency CHAR(3) NOT NULL CHECK (currency IN ('USD','EUR','GBP')),
    usd_per_unit NUMERIC(12,6) NOT NULL CHECK (usd_per_unit > 0),
    PRIMARY KEY (rate_date, currency)
);
CREATE TABLE IF NOT EXISTS players (
    player_id BIGINT PRIMARY KEY,
    display_name TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL,
    country CHAR(2),
    platform TEXT NOT NULL CHECK (platform IN ('ios','android')),
    acquisition_channel TEXT NOT NULL CHECK (acquisition_channel IN ('organic','paid_social','paid_search','creator')),
    campaign_id INTEGER REFERENCES campaigns,
    CHECK (acquisition_channel <> 'organic' OR campaign_id IS NULL)
);
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL CHECK (ends_at > starts_at),
    eligibility_rule TEXT NOT NULL,
    exposure_trigger TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_variants (
    experiment_id INTEGER NOT NULL REFERENCES experiments,
    variant TEXT NOT NULL,
    allocation NUMERIC(5,4) NOT NULL CHECK (allocation > 0 AND allocation <= 1),
    PRIMARY KEY (experiment_id, variant)
);
CREATE TABLE IF NOT EXISTS experiment_assignments (
    experiment_id INTEGER NOT NULL,
    player_id BIGINT NOT NULL REFERENCES players,
    variant TEXT NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (experiment_id, player_id),
    FOREIGN KEY (experiment_id, variant) REFERENCES experiment_variants
);
CREATE TABLE IF NOT EXISTS sessions (
    session_id BIGINT PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players,
    session_number INTEGER NOT NULL CHECK (session_number > 0),
    release_id INTEGER NOT NULL REFERENCES game_releases,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL CHECK (ended_at > started_at),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0),
    status TEXT NOT NULL CHECK (status IN ('completed','interrupted')),
    CHECK (ended_at = started_at + duration_seconds * INTERVAL '1 second'),
    UNIQUE (player_id, session_number),
    UNIQUE (session_id, player_id),
    UNIQUE (session_id, release_id)
);
CREATE TABLE IF NOT EXISTS experiment_exposures (
    experiment_id INTEGER NOT NULL,
    player_id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    exposed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (experiment_id, player_id),
    FOREIGN KEY (experiment_id, player_id) REFERENCES experiment_assignments,
    FOREIGN KEY (session_id, player_id) REFERENCES sessions (session_id, player_id)
);
CREATE TABLE IF NOT EXISTS level_attempts (
    attempt_id BIGINT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    release_id INTEGER NOT NULL,
    level_id INTEGER NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NOT NULL CHECK (ended_at > started_at),
    outcome TEXT NOT NULL CHECK (outcome IN ('completed','failed','abandoned')),
    FOREIGN KEY (session_id, release_id) REFERENCES sessions (session_id, release_id),
    FOREIGN KEY (level_id, release_id) REFERENCES level_configurations,
    UNIQUE (session_id, attempt_number),
    UNIQUE (attempt_id, session_id)
);
CREATE TABLE IF NOT EXISTS purchases (
    purchase_id BIGINT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    player_id BIGINT NOT NULL,
    item_id INTEGER NOT NULL REFERENCES items,
    initiated_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('pending','completed','failed')),
    currency CHAR(3) NOT NULL,
    rate_date DATE NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    revenue_usd NUMERIC(12,2) NOT NULL CHECK (revenue_usd >= 0),
    FOREIGN KEY (session_id, player_id) REFERENCES sessions (session_id, player_id),
    FOREIGN KEY (rate_date, currency) REFERENCES exchange_rates,
    CHECK (rate_date = (initiated_at AT TIME ZONE 'UTC')::date),
    CHECK ((status = 'pending' AND resolved_at IS NULL) OR (status <> 'pending' AND resolved_at >= initiated_at)),
    CHECK ((status = 'completed' AND revenue_usd > 0) OR (status <> 'completed' AND revenue_usd = 0)),
    UNIQUE (purchase_id, session_id)
);
CREATE TABLE IF NOT EXISTS events (
    event_id BIGINT PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES sessions,
    event_sequence INTEGER NOT NULL CHECK (event_sequence > 0),
    event_timestamp TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL CHECK (received_at >= event_timestamp),
    event_type TEXT NOT NULL CHECK (event_type IN (
      'session_start','session_end','level_start','level_complete','level_failed',
      'player_died','level_retry','reward_claimed','shop_opened','purchase_started',
      'purchase_completed','tutorial_started','tutorial_completed')),
    attempt_id BIGINT,
    purchase_id BIGINT,
    properties JSONB NOT NULL CHECK (jsonb_typeof(properties) = 'object'),
    FOREIGN KEY (attempt_id, session_id) REFERENCES level_attempts (attempt_id, session_id),
    FOREIGN KEY (purchase_id, session_id) REFERENCES purchases (purchase_id, session_id),
    UNIQUE (session_id, event_sequence)
);
CREATE TABLE IF NOT EXISTS generation_runs (
    run_id INTEGER PRIMARY KEY CHECK (run_id = 1),
    generator_version TEXT NOT NULL,
    profile TEXT NOT NULL,
    seed BIGINT NOT NULL,
    player_count INTEGER NOT NULL CHECK (player_count > 0),
    observation_start TIMESTAMPTZ NOT NULL,
    observation_end TIMESTAMPTZ NOT NULL CHECK (observation_end > observation_start),
    content_sha256 TEXT NOT NULL,
    row_counts JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_player_time ON sessions (player_id, started_at);
CREATE INDEX IF NOT EXISTS sessions_release ON sessions (release_id);
CREATE INDEX IF NOT EXISTS attempts_level_release ON level_attempts (level_id, release_id);
CREATE INDEX IF NOT EXISTS purchases_player_time ON purchases (player_id, initiated_at);
CREATE INDEX IF NOT EXISTS events_event_time ON events (event_timestamp);
CREATE INDEX IF NOT EXISTS events_received_time ON events (received_at);
CREATE INDEX IF NOT EXISTS events_attempt_type ON events (attempt_id, event_type) WHERE attempt_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS events_purchase_type ON events (purchase_id, event_type) WHERE purchase_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS events_session_type ON events (session_id, event_type);
