PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_agricultural_records;
DROP TABLE IF EXISTS extraction_runs;
DROP TABLE IF EXISTS dim_crops;
DROP TABLE IF EXISTS dim_locations;
DROP TABLE IF EXISTS dim_sources;

CREATE TABLE dim_sources (
    source_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_group TEXT NOT NULL,
    period_of_info TEXT,
    assigned_agent TEXT NOT NULL,
    implementation_status TEXT NOT NULL,
    known_limitations TEXT
);

CREATE TABLE extraction_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    extracting_agent TEXT NOT NULL,
    llm_model_used TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    latency_ms REAL DEFAULT 115.0,
    tokens_used INTEGER DEFAULT 420,
    retry_count INTEGER DEFAULT 0,
    manual_intervention_used INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id)
);

CREATE TABLE dim_locations (
    location_id TEXT PRIMARY KEY,
    canonical_district_name TEXT NOT NULL,
    agro_climatic_zone TEXT NOT NULL,
    state_name TEXT DEFAULT 'Assam'
);

CREATE TABLE dim_crops (
    crop_id TEXT PRIMARY KEY,
    crop_name TEXT NOT NULL,
    variety_name TEXT NOT NULL,
    season TEXT NOT NULL
);

CREATE TABLE fact_agricultural_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_hash TEXT UNIQUE NOT NULL,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    run_id TEXT NOT NULL,
    extracting_agent TEXT NOT NULL,
    source_location TEXT NOT NULL,
    location_id TEXT NOT NULL,
    crop_id TEXT NOT NULL,
    time_period TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    raw_value_text TEXT NOT NULL,
    raw_unit TEXT NOT NULL,
    normalized_value REAL NOT NULL,
    normalized_unit TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES dim_sources(source_id),
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id),
    FOREIGN KEY (location_id) REFERENCES dim_locations(location_id),
    FOREIGN KEY (crop_id) REFERENCES dim_crops(crop_id),
    UNIQUE(source_id, source_location, crop_id, location_id, time_period, metric_name)
);
