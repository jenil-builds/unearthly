"""Fault-Isolated Source-of-Truth Ingestion Pipeline (ingestion/pipeline.py)."""
import csv
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ingestion.adapters import build_default_registry
from ingestion.ai_runtime import AIRuntime
from ingestion.base_adapter import AdapterRegistry
from ingestion.models import FetchSummary, RawFetchResult, SourceConfig
from ingestion.storage import IngestionStorage, make_unique_run_id, utc_now_iso
from ingestion.validator import ZeroFabricationValidator

AGENT1_TRIAGE_PROMPT = (
    "You are Agent 1 (Semantic Document Triage) for an Assam agricultural knowledge base. "
    "Inspect the fetched document preview and determine whether it contains real agricultural data "
    "(statistics, crop varieties, yields, prices, cold storage, soil/GIS metadata) or is a non-data "
    "error/login/captcha/404 page.\n"
    'Return ONLY JSON: {"is_agricultural_data": true|false, "language": "en"|"as"|"mixed", "reason": str}'
)


def infer_adapter_type(source_group: str, url: str) -> str:
    ext = os.path.splitext(urlparse(url).path if url.startswith(("http://", "https://")) else url)[1].lower()
    if ext == ".csv":
        return "csv_feed"
    if ext == ".pdf":
        return "pdf_table"
    if ext in (".txt", ".md"):
        return "unstructured_text"
    if source_group in ("Geospatial_GIS", "Database_Dashboard"):
        return "wms_gis"
    if source_group == "Document_PDF":
        return "pdf_table"
    return "html_table"


def load_sources_from_csv(csv_path: str = "docs/source_agent_map.csv") -> List[SourceConfig]:
    configs: List[SourceConfig] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row["url"].strip()
            sgroup = row["source_group"].strip()
            assigned = row["assigned_agent"].strip()
            if assigned not in ("agent2_ingestion", "agent2b_live_gis"):
                assigned = "agent2b_live_gis" if sgroup in ("Geospatial_GIS", "Database_Dashboard") else "agent2_ingestion"
            configs.append(
                SourceConfig(
                    source_id=row["source_id"].strip(),
                    source_name=row["source_name"].strip(),
                    url=url,
                    source_group=sgroup,
                    adapter_type=row.get("adapter_type", "").strip() or infer_adapter_type(sgroup, url),
                    assigned_agent=assigned,
                    temporal_coverage=row.get("temporal_coverage", "Current").strip() or "Current",
                    implementation_status=row.get("implementation_status", "done").strip() or "done",
                    known_limitations=row.get("known_limitations", "").strip(),
                    refresh_interval_minutes=int(
                        row.get("refresh_interval_minutes") or (60 if sgroup == "Database_Dashboard" else 1440)
                    ),
                )
            )
    return configs


class SourceOfTruthPipeline:
    def __init__(
        self,
        storage: Optional[IngestionStorage] = None,
        registry: Optional[AdapterRegistry] = None,
        ai_runtime: Optional[AIRuntime] = None,
        validator: Optional[ZeroFabricationValidator] = None,
        enable_ai_triage: bool = True,
    ) -> None:
        self.storage = storage or IngestionStorage()
        self.registry = registry or build_default_registry()
        self.ai = ai_runtime or AIRuntime()
        self.validator = validator or ZeroFabricationValidator(ai_runtime=self.ai)
        self.enable_ai_triage = enable_ai_triage
        self.storage.init_schema()

    @staticmethod
    def _build_triage_preview(raw: RawFetchResult, max_chars: int = 3000) -> str:
        decoded = raw.raw_bytes.decode("utf-8", errors="replace")
        is_html = "html" in (raw.content_type or "").lower() or decoded.lstrip()[:50].lower().startswith(("<!doctype", "<html"))
        if is_html:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(decoded, "html.parser")
                for tag in soup(["script", "style", "head", "noscript"]):
                    tag.decompose()
                visible = " ".join(soup.get_text(" ", strip=True).split())
                if visible:
                    return visible[:max_chars]
            except Exception:
                pass
            stripped = re.sub(r"(?is)<(script|style|head|noscript).*?>.*?</\1>", " ", decoded)
            stripped = re.sub(r"<[^>]+>", " ", stripped)
            return " ".join(stripped.split())[:max_chars]
        return decoded[:max_chars]

    def _triage_payload(self, cfg: SourceConfig, raw: RawFetchResult) -> Tuple[bool, int, Optional[str], Optional[str]]:
        if not self.enable_ai_triage or "pdf" in raw.content_type or raw.source_url.lower().endswith(".pdf"):
            return True, 0, None, None
        preview = self._build_triage_preview(raw, max_chars=3000)
        res = self.ai.call_json(
            "agent1_classifier",
            AGENT1_TRIAGE_PROMPT,
            json.dumps(
                {
                    "source_id": cfg.source_id,
                    "source_name": cfg.source_name,
                    "content_type": raw.content_type,
                    "preview": preview,
                },
                ensure_ascii=False,
            ),
        )
        if res.used_fallback or not isinstance(res.parsed_json, dict):
            return True, 0, None, None
        is_data = bool(res.parsed_json.get("is_agricultural_data", True))
        return is_data, res.tokens_used, res.model_id, (None if is_data else str(res.parsed_json.get("reason") or "Non-agricultural page"))

    def run_source(self, cfg: SourceConfig, force: bool = False) -> FetchSummary:
        t0 = time.perf_counter()
        run_id = make_unique_run_id(cfg.source_id)
        self.storage.register_source(cfg)
        prev = self.storage.get_source_health(cfg.source_id) or {}
        prev_etag, prev_lm, prev_sha = (
            (None, None, None) if force else (prev.get("last_etag"), prev.get("last_modified"), prev.get("last_content_sha256"))
        )
        raw = RawFetchResult(cfg.source_id, cfg.url, utc_now_iso(), None, False)
        triage_tokens, model_used = 0, "deterministic_fallback"
        try:
            adapter = self.registry.get(cfg.adapter_type)
            if hasattr(adapter, "mapper") and hasattr(adapter.mapper, "ai"):
                adapter.mapper.ai = self.ai
            if hasattr(adapter, "html_helper") and hasattr(adapter.html_helper, "mapper"):
                adapter.html_helper.mapper.ai = self.ai
            raw = adapter.fetch(cfg, etag=prev_etag, last_modified=prev_lm)
            if raw.error_message:
                lat = round((time.perf_counter() - t0) * 1000.0, 2)
                self.storage.record_run_and_records(cfg, run_id, raw, [], 0, 0, "FAILED", lat, 0, model_used, raw.error_message)
                return FetchSummary(run_id, cfg.source_id, cfg.adapter_type, "FAILED", raw.http_status, latency_ms=lat, error_message=raw.error_message)
            if raw.not_modified or (prev_sha and raw.content_sha256 and raw.content_sha256 == prev_sha):
                lat = round((time.perf_counter() - t0) * 1000.0, 2)
                self.storage.record_run_and_records(cfg, run_id, raw, [], 0, 0, "NOT_MODIFIED", lat, 0, model_used)
                return FetchSummary(run_id, cfg.source_id, cfg.adapter_type, "NOT_MODIFIED", raw.http_status, latency_ms=lat)

            should_parse, triage_tokens, triage_model, skip_reason = self._triage_payload(cfg, raw)
            if triage_model:
                model_used = triage_model
            if not should_parse:
                lat = round((time.perf_counter() - t0) * 1000.0, 2)
                self.storage.record_run_and_records(cfg, run_id, raw, [], 0, 0, "SKIPPED_NON_DATA", lat, triage_tokens, model_used, skip_reason)
                return FetchSummary(run_id, cfg.source_id, cfg.adapter_type, "SKIPPED_NON_DATA", raw.http_status, latency_ms=lat, error_message=skip_reason)

            extracted = adapter.parse(cfg, raw)
            src_text = None if ("pdf" in raw.content_type or raw.source_url.lower().endswith(".pdf")) else raw.raw_bytes.decode("utf-8", errors="replace")
            valid_norm, rejected, val_tokens, val_model = self.validator.validate_batch(extracted, source_text=src_text)
            if val_model:
                model_used = val_model
            if not extracted:
                status, err_msg = "EMPTY_PARSE", "Adapter parsed 0 records from source payload."
            elif not valid_norm and rejected:
                status, err_msg = "FAILED", f"All {len(rejected)} extracted records failed grounding/validation: {rejected[0]}"
            elif rejected:
                status, err_msg = "PARTIAL", f"{len(rejected)} record(s) rejected: {rejected[0]}"
            else:
                status, err_msg = "UPDATED", None

            lat = round((time.perf_counter() - t0) * 1000.0, 2)
            committed = self.storage.record_run_and_records(
                cfg, run_id, raw, valid_norm, len(extracted), len(rejected), status, lat, triage_tokens + val_tokens, model_used, err_msg
            )
            return FetchSummary(run_id, cfg.source_id, cfg.adapter_type, status, raw.http_status, len(extracted), committed, len(rejected), lat, err_msg, rejected)
        except Exception as exc:
            lat = round((time.perf_counter() - t0) * 1000.0, 2)
            err_msg = f"{type(exc).__name__}: {exc}"
            self.storage.record_run_and_records(cfg, run_id, raw, [], 0, 0, "FAILED", lat, triage_tokens, model_used, err_msg)
            return FetchSummary(run_id, cfg.source_id, cfg.adapter_type, "FAILED", raw.http_status, latency_ms=lat, error_message=err_msg)

    def run_sources(self, configs: List[SourceConfig], max_workers: int = 4, force: bool = False) -> List[FetchSummary]:
        if not configs:
            return []
        if max_workers <= 1 or len(configs) == 1:
            return [self.run_source(c, force=force) for c in configs]
        summaries: Dict[str, FetchSummary] = {}
        with ThreadPoolExecutor(max_workers=min(max_workers, len(configs))) as pool:
            fmap = {pool.submit(self.run_source, cfg, force): cfg.source_id for cfg in configs}
            for fut in as_completed(fmap):
                summaries[fmap[fut]] = fut.result()
        return [summaries[c.source_id] for c in configs]
