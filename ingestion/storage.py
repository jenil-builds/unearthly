"""SQLite WAL-Mode Storage, Freshness Tracking & Source Health Persistence (ingestion/storage.py)."""
import os, sqlite3, uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ingestion.models import RawFetchResult, SourceConfig

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def make_unique_run_id(source_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"RUN_{source_id}_{ts}_{uuid.uuid4().hex[:6].upper()}"

class IngestionStorage:
    def __init__(self, db_path: str = "db/assam_agri_phase2.db", schema_path: str = "db/schema.sql") -> None:
        self.db_path = db_path
        self.schema_path = schema_path

    def _connect(self, isolation_level: Optional[str] = "") -> sqlite3.Connection:
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=isolation_level)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        return conn

    def init_schema(self) -> None:
        with open(self.schema_path, "r", encoding="utf-8-sig") as sf:
            ddl = sf.read()
        conn = self._connect()
        try:
            conn.executescript(ddl)
            row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='source_fetch_log'").fetchone()
            if row and "EMPTY_PARSE" not in (row["sql"] or ""):
                conn.execute("PRAGMA foreign_keys = OFF;")
                conn.execute("ALTER TABLE source_fetch_log RENAME TO source_fetch_log_old;")
                conn.executescript(ddl)
                conn.execute(
                    "INSERT INTO source_fetch_log (fetch_id, run_id, source_id, source_url, adapter_type, fetched_at_utc, http_status, etag, last_modified, content_sha256, bytes_fetched, records_extracted, records_committed, records_rejected, fetch_status, error_message) "
                    "SELECT fetch_id, run_id, source_id, source_url, adapter_type, fetched_at_utc, http_status, etag, last_modified, content_sha256, bytes_fetched, records_extracted, records_committed, records_rejected, fetch_status, error_message FROM source_fetch_log_old;"
                )
                conn.execute("DROP TABLE source_fetch_log_old;")
                conn.execute("PRAGMA foreign_keys = ON;")
            conn.commit()
        finally:
            conn.close()

    def register_source(self, cfg: SourceConfig) -> None:
        conn = self._connect(isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("INSERT OR REPLACE INTO dim_sources (source_id, source_name, url, source_group, temporal_coverage, assigned_agent, implementation_status, known_limitations) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (cfg.source_id, cfg.source_name, cfg.url, cfg.source_group, cfg.temporal_coverage, cfg.assigned_agent, cfg.implementation_status, cfg.known_limitations))
            conn.execute("INSERT OR IGNORE INTO source_health (source_id, health_status, refresh_interval_minutes) VALUES (?, 'UNKNOWN', ?)", (cfg.source_id, cfg.refresh_interval_minutes))
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        finally:
            conn.close()

    def get_source_health(self, source_id: str) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM source_health WHERE source_id = ?", (source_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_all_source_health(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT h.*, s.source_name, s.url, s.source_group, s.assigned_agent FROM source_health h JOIN dim_sources s ON h.source_id = s.source_id ORDER BY h.source_id ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def record_run_and_records(self, cfg: SourceConfig, run_id: str, raw_fetch: RawFetchResult, normalized_records: List[Dict[str, Any]], records_extracted: int, records_rejected: int, fetch_status: str, latency_ms: float, tokens_used: int, llm_model_id: str, error_message: Optional[str] = None) -> int:
        now_iso = utc_now_iso()
        run_status = "FAILED" if fetch_status == "FAILED" else ("PARTIAL" if fetch_status in ("PARTIAL", "EMPTY_PARSE") else "COMPLETED")
        manual_used = 1 if cfg.source_group == "Geospatial_GIS" else 0
        total_retries = sum(int(r.get("retries", 0)) for r in normalized_records)
        conn = self._connect(isolation_level=None)
        committed = 0
        try:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("INSERT INTO extraction_runs (run_id, source_id, agent_name, llm_model_id, started_at_utc, completed_at_utc, latency_ms, tokens_used, retry_count, manual_interventions, run_status, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, cfg.source_id, cfg.assigned_agent, llm_model_id, raw_fetch.fetched_at_utc, now_iso, round(latency_ms, 2), int(tokens_used), total_retries, manual_used, run_status, error_message))
            for r in normalized_records:
                conn.execute("INSERT OR REPLACE INTO dim_locations (location_id, canonical_district_name, agro_climatic_zone, state_name) VALUES (?, ?, ?, 'Assam')", (r["location_id"], r["canonical_district"], r["agro_climatic_zone"]))
                conn.execute("INSERT OR REPLACE INTO dim_crops (crop_id, crop_name, variety_name, season_category) VALUES (?, ?, ?, ?)", (r["crop_id"], r["crop_name"], r["variety_name"], r["season_category"]))
                conn.execute("INSERT OR REPLACE INTO fact_agricultural_records (record_hash, source_id, source_type, run_id, extracting_agent, source_location, location_id, crop_id, time_period, metric_name, raw_value_text, raw_unit, normalized_value, normalized_unit, validation_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (r["record_hash"], r["source_id"], r["source_type"], run_id, r["agent"], r["locator"], r["location_id"], r["crop_id"], r["time_period"], r["metric_name"], str(r["raw_value"]), r["raw_unit"], r["normalized_value"], r["normalized_unit"], r["validation_status"]))
                committed += 1
            fetch_id = f"FETCH_{uuid.uuid4().hex[:12].upper()}"
            conn.execute("INSERT INTO source_fetch_log (fetch_id, run_id, source_id, source_url, adapter_type, fetched_at_utc, http_status, etag, last_modified, content_sha256, bytes_fetched, records_extracted, records_committed, records_rejected, fetch_status, error_message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (fetch_id, run_id, cfg.source_id, raw_fetch.source_url, cfg.adapter_type, raw_fetch.fetched_at_utc, raw_fetch.http_status, raw_fetch.etag, raw_fetch.last_modified, raw_fetch.content_sha256, len(raw_fetch.raw_bytes), records_extracted, committed, records_rejected, fetch_status, error_message))
            prev = conn.execute("SELECT consecutive_failures, last_success_at_utc, last_data_changed_at_utc, last_etag, last_modified, last_content_sha256 FROM source_health WHERE source_id = ?", (cfg.source_id,)).fetchone()
            prev_failures = int(prev["consecutive_failures"]) if prev else 0
            if fetch_status == "FAILED":
                new_failures = prev_failures + 1
                health_status = "UNHEALTHY" if new_failures >= 3 else "DEGRADED"
                last_success = prev["last_success_at_utc"] if prev else None
                last_changed = prev["last_data_changed_at_utc"] if prev else None
                new_etag, new_lm, new_sha = (prev["last_etag"], prev["last_modified"], prev["last_content_sha256"]) if prev else (None, None, None)
                recorded_err = error_message
            elif fetch_status in ("SKIPPED_NON_DATA", "EMPTY_PARSE"):
                new_failures = prev_failures
                health_status = "DEGRADED"
                last_success = prev["last_success_at_utc"] if prev else None
                last_changed = prev["last_data_changed_at_utc"] if prev else None
                new_etag, new_lm, new_sha = (prev["last_etag"], prev["last_modified"], prev["last_content_sha256"]) if prev else (None, None, None)
                recorded_err = error_message or f"Source returned {fetch_status}"
            else:
                new_failures = 0
                health_status = "DEGRADED" if fetch_status == "PARTIAL" else "HEALTHY"
                last_success = now_iso
                changed = fetch_status in ("UPDATED", "PARTIAL") and raw_fetch.content_sha256 is not None and (not prev or prev["last_content_sha256"] != raw_fetch.content_sha256)
                last_changed = now_iso if changed else (prev["last_data_changed_at_utc"] if prev else now_iso)
                new_etag = raw_fetch.etag or (prev["last_etag"] if prev else None)
                new_lm = raw_fetch.last_modified or (prev["last_modified"] if prev else None)
                new_sha = raw_fetch.content_sha256 or (prev["last_content_sha256"] if prev else None)
                recorded_err = error_message if fetch_status == "PARTIAL" else None
            conn.execute(
                """INSERT INTO source_health (source_id, health_status, last_checked_at_utc, last_success_at_utc, last_data_changed_at_utc, last_http_status, consecutive_failures, last_error, last_etag, last_modified, last_content_sha256, refresh_interval_minutes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_id) DO UPDATE SET health_status=excluded.health_status, last_checked_at_utc=excluded.last_checked_at_utc, last_success_at_utc=excluded.last_success_at_utc, last_data_changed_at_utc=excluded.last_data_changed_at_utc, last_http_status=excluded.last_http_status, consecutive_failures=excluded.consecutive_failures, last_error=excluded.last_error, last_etag=excluded.last_etag, last_modified=excluded.last_modified, last_content_sha256=excluded.last_content_sha256, refresh_interval_minutes=excluded.refresh_interval_minutes""",
                (cfg.source_id, health_status, now_iso, last_success, last_changed, raw_fetch.http_status, new_failures, recorded_err, new_etag, new_lm, new_sha, cfg.refresh_interval_minutes),
            )
            conn.execute("COMMIT;")
            return committed
        except Exception:
            conn.execute("ROLLBACK;")
            raise
        finally:
            conn.close()
