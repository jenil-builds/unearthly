-- AgriAgent Phase 2 Relational Schema (SQLite)
-- Multi-Agent Pipeline: agent1_classifier -> agent2_ingestion / agent2b_live_gis -> agent3_task

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_sources (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    url TEXT NOT NULL,
    source_group TEXT NOT NULL,
    temporal_coverage TEXT NOT NULL,
    assigned_agent TEXT NOT NULL CHECK (assigned_agent IN ('agent2_ingestion', 'agent2b_live_gis')),
    implementation_status TEXT NOT NULL CHECK (implementation_status IN ('done', 'partial', 'pending')),
    known_limitations TEXT
);

CREATE TABLE IF NOT EXISTS dim_locations (
    location_id TEXT PRIMARY KEY CHECK (location_id LIKE 'LGD_AS_%'),
    canonical_district_name TEXT NOT NULL,
    agro_climatic_zone TEXT NOT NULL,
    state_name TEXT NOT NULL DEFAULT 'Assam'
);

CREATE TABLE IF NOT EXISTS dim_crops (
    crop_id TEXT PRIMARY KEY,
    crop_name TEXT NOT NULL,
    variety_name TEXT NOT NULL DEFAULT 'General',
    season_category TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    agent_name TEXT NOT NULL CHECK (agent_name IN ('agent2_ingestion', 'agent2b_live_gis')),
    llm_model_id TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    tokens_used INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    manual_interventions INTEGER NOT NULL DEFAULT 0,
    run_status TEXT NOT NULL CHECK (run_status IN ('COMPLETED', 'PARTIAL', 'FAILED')),
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id)
);

CREATE TABLE IF NOT EXISTS fact_agricultural_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_hash TEXT NOT NULL UNIQUE,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    run_id TEXT NOT NULL,
    extracting_agent TEXT NOT NULL CHECK (extracting_agent IN ('agent2_ingestion', 'agent2b_live_gis')),
    source_location TEXT NOT NULL,
    location_id TEXT NOT NULL,
    crop_id TEXT NOT NULL,
    time_period TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    raw_value_text TEXT NOT NULL,
    raw_unit TEXT NOT NULL,
    normalized_value REAL NOT NULL CHECK (normalized_value > 0 AND normalized_value <= 1e12),
    normalized_unit TEXT NOT NULL CHECK (normalized_unit IN ('ha', 'tonnes', 'kg/ha', 'INR', 'Rs/Quintal', 'mm', 'days', 'meters', 'scale', 'pH')),
    validation_status TEXT NOT NULL CHECK (validation_status IN ('VALIDATED', 'SELF_CORRECTED')),
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id),
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id),
    FOREIGN KEY (location_id) REFERENCES dim_locations(location_id),
    FOREIGN KEY (crop_id) REFERENCES dim_crops(crop_id),
    UNIQUE (
        source_id,
        source_location,
        crop_id,
        location_id,
        time_period,
        metric_name
    )
);

CREATE INDEX IF NOT EXISTS idx_fact_source ON fact_agricultural_records(source_id);
CREATE INDEX IF NOT EXISTS idx_fact_agent ON fact_agricultural_records(extracting_agent);
CREATE INDEX IF NOT EXISTS idx_fact_location ON fact_agricultural_records(location_id);
CREATE INDEX IF NOT EXISTS idx_fact_crop ON fact_agricultural_records(crop_id);
CREATE TABLE IF NOT EXISTS source_fetch_log (
    fetch_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    adapter_type TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL,
    http_status INTEGER,
    etag TEXT,
    last_modified TEXT,
    content_sha256 TEXT,
    bytes_fetched INTEGER NOT NULL DEFAULT 0,
    records_extracted INTEGER NOT NULL DEFAULT 0,
    records_committed INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    fetch_status TEXT NOT NULL CHECK (fetch_status IN ('UPDATED', 'NOT_MODIFIED', 'PARTIAL', 'FAILED', 'SKIPPED_NON_DATA', 'EMPTY_PARSE')),
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id),
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id)
);

CREATE TABLE IF NOT EXISTS source_health (
    source_id TEXT PRIMARY KEY,
    health_status TEXT NOT NULL CHECK (health_status IN ('HEALTHY', 'DEGRADED', 'UNHEALTHY', 'UNKNOWN')) DEFAULT 'UNKNOWN',
    last_checked_at_utc TEXT,
    last_success_at_utc TEXT,
    last_data_changed_at_utc TEXT,
    last_http_status INTEGER,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_etag TEXT,
    last_modified TEXT,
    last_content_sha256 TEXT,
    refresh_interval_minutes INTEGER NOT NULL DEFAULT 1440 CHECK (refresh_interval_minutes > 0),
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_fetch_log_source ON source_fetch_log(source_id, fetched_at_utc);
CREATE INDEX IF NOT EXISTS idx_source_health_status ON source_health(health_status);
