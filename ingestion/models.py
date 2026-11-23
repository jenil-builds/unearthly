"""Strict data contracts for the Source-of-Truth Ingestion System."""
from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    source_name: str
    url: str
    source_group: str
    adapter_type: str
    assigned_agent: str
    temporal_coverage: str = "Current"
    implementation_status: str = "done"
    known_limitations: str = ""
    refresh_interval_minutes: int = 1440

@dataclass
class RawFetchResult:
    source_id: str
    source_url: str
    fetched_at_utc: str
    http_status: Optional[int]
    not_modified: bool
    raw_bytes: bytes = b""
    content_type: str = ""
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    content_sha256: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class SourceRecord:
    source_id: str
    source_url: str
    source_type: str
    extracting_agent: str
    locator: str
    crop_name: str
    variety_name: str
    district_raw: str
    time_period: str
    metric_name: str
    raw_value: str
    raw_unit: str
    verbatim_quote: str
    fetched_at_utc: str
    llm_model_id: str = "deterministic_parser"
    tokens_used: int = 0
    latency_ms: float = 0.0
    is_structured_table: bool = False

@dataclass
class AIResponse:
    parsed_json: Optional[Any]
    raw_text: str
    provider: str
    model_id: str
    tokens_used: int
    latency_ms: float
    used_fallback: bool
    error: Optional[str] = None

@dataclass
class FetchSummary:
    run_id: str
    source_id: str
    adapter_type: str
    fetch_status: str
    http_status: Optional[int]
    records_extracted: int = 0
    records_committed: int = 0
    records_rejected: int = 0
    latency_ms: float = 0.0
    error_message: Optional[str] = None
    rejected_reasons: List[str] = field(default_factory=list)
