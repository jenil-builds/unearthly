# Database Data Dictionary & Validation Rules (`db/dictionary.md`)

## 1. Core Star-Schema Tables
* **`dim_sources`**: Master catalog of registered Assam agricultural sources (`source_id`, `source_name`, `url`, `source_group`, `assigned_agent`, `implementation_status`, `known_limitations`).
* **`dim_locations`**: Canonical Assam district registry keyed by Local Government Directory code (`location_id LIKE 'LGD_AS_%'`), `canonical_district_name`, `agro_climatic_zone`, and `state_name`.
* **`dim_crops`**: Crop & variety registry (`crop_id`, `crop_name`, `variety_name`, `season_category`).
* **`extraction_runs`**: Full historical execution log (`run_id`, `source_id`, `agent_name`, `llm_model_id`, `started_at_utc`, `completed_at_utc`, `latency_ms`, `tokens_used`, `retry_count`, `manual_interventions`, `run_status IN ('COMPLETED', 'PARTIAL', 'FAILED')`, `error_message`).
* **`fact_agricultural_records`**: Normalized agricultural facts with `NOT NULL` provenance (`source_id`, `run_id`, `extracting_agent`, `source_location`, `location_id`, `crop_id`, `time_period`, `metric_name`, `raw_value_text`, `raw_unit`, `normalized_value`, `normalized_unit`, `validation_status IN ('VALIDATED', 'SELF_CORRECTED')`) and composite natural-key + SHA-256 `record_hash` deduplication.

## 2. Source-of-Truth Ingestion & Monitoring Tables
* **`source_fetch_log`**: Immutable per-fetch audit log (`fetch_id`, `run_id`, `source_id`, `source_url`, `adapter_type`, `fetched_at_utc`, `http_status`, `etag`, `last_modified`, `content_sha256`, `bytes_fetched`, `records_extracted`, `records_committed`, `records_rejected`, `fetch_status IN ('UPDATED', 'NOT_MODIFIED', 'PARTIAL', 'FAILED', 'SKIPPED_NON_DATA', 'EMPTY_PARSE')`, `error_message`).
* **`source_health`**: Current operational health and freshness cache per source (`source_id`, `health_status IN ('HEALTHY', 'DEGRADED', 'UNHEALTHY', 'UNKNOWN')`, `last_checked_at_utc`, `last_success_at_utc`, `last_data_changed_at_utc`, `last_http_status`, `consecutive_failures`, `last_error`, `last_etag`, `last_modified`, `last_content_sha256`, `refresh_interval_minutes > 0`).

## 3. Allowed SI Units & Deterministic Conversions (`agent3_task.py`)
`normalized_unit` is restricted by SQL `CHECK` constraint to:
`ha`, `tonnes`, `kg/ha`, `INR`, `Rs/Quintal`, `mm`, `days`, `meters`, `scale`, `pH`.

* `Hectares` / `ha` -> `ha`
* `Tonnes` / `MT` -> `tonnes`
* `q/ha` / `quintal/ha` -> `kg/ha` (x 100)
* `t/ha` / `MT/ha` / `tonnes/ha` -> `kg/ha` (x 1000)
* `Rs. Lakh` / `Lakh INR` -> `INR` (x 100000)
* `Rs/Quintal` -> `Rs/Quintal`
