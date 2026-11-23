"""AI Schema-Once Table Mapper & Citation-Anchored Text Extractor."""
import json, unicodedata
from typing import Any, Dict, List, Optional, Tuple
from agent2_ingestion import AISemanticExtractor, ASSAMESE_DIGIT_MAP
from ingestion.ai_runtime import AIRuntime
from ingestion.models import SourceConfig, SourceRecord

TABLE_MAPPER_SYSTEM_PROMPT = (
    "You are an agricultural data schema mapper for Assam, India. "
    "Given table column headers and up to 3 sample rows, return ONLY a JSON object mapping column names "
    "to canonical fields. NEVER invent values. If a field has no matching column, set it to null.\n"
    'Output JSON schema: {"crop_col": str|null, "variety_col": str|null, "district_col": str|null, '
    '"time_period_col": str|null, "metric_name_col": str|null, "raw_value_col": str|null, '
    '"raw_unit_col": str|null, "wide_metric_cols": [{"col": str, "metric_name": str, "unit": str}]}'
)

UNSTRUCTURED_SYSTEM_PROMPT = (
    "You are a strict extractive agricultural information extractor for Assam (English & Assamese). "
    "Extract ONLY facts explicitly stated in the source text. NEVER predict, infer, or fabricate numbers, "
    "districts, crops, periods, or units. Every extracted record MUST include a 'verbatim_quote' copied "
    "character-for-character from the source text containing the raw_value.\n"
    'Return ONLY a JSON object: {"records": [{"crop_name": str, "variety_name": str, "district_raw": str, '
    '"time_period": str, "metric_name": str, "raw_value": str, "raw_unit": str, "verbatim_quote": str}]}. '
    'Return {"records": []} if no factual metrics exist.'
)

def _nfc(text: Any) -> str:
    return unicodedata.normalize("NFC", str(text or "")).strip()

def _deterministic_header_mapping(headers: List[str]) -> Dict[str, Any]:
    lower_map = {_nfc(h).lower(): h for h in headers if h}
    def pick(*candidates: str) -> Optional[str]:
        for c in candidates:
            if c in lower_map:
                return lower_map[c]
        return None
    mapping: Dict[str, Any] = {
        "crop_col": pick("crop_name", "crop", "commodity", "শস্য"),
        "variety_col": pick("variety_name", "variety", "cultivar", "জাত"),
        "district_col": pick("district_raw", "district", "location", "market", "জিলা"),
        "time_period_col": pick("time_period", "period", "year", "season", "বৰ্ষ"),
        "metric_name_col": pick("metric_name", "metric", "parameter", "variable"),
        "raw_value_col": pick("raw_value", "value", "val"),
        "raw_unit_col": pick("raw_unit", "unit", "units"),
        "wide_metric_cols": [],
    }
    if not mapping["raw_value_col"]:
        for h_low, h_orig in lower_map.items():
            if any(k in h_low for k in ("area", "production", "yield", "price", "value")):
                if "area" in h_low:
                    m_name, unit = "Area", ("ha" if "ha" in h_low else "Hectares")
                elif "production" in h_low:
                    m_name, unit = "Production", "Tonnes"
                elif "yield" in h_low:
                    m_name, unit = "Yield", ("q/ha" if "q" in h_low else "kg/ha")
                elif "price" in h_low:
                    m_name, unit = "Modal_Price", "Rs/Quintal"
                else:
                    m_name, unit = "Value", ("Rs. Lakh" if "lakh" in h_low else "INR")
                mapping["wide_metric_cols"].append({"col": h_orig, "metric_name": m_name, "unit": unit})
    return mapping

class AISchemaMapper:
    def __init__(self, ai_runtime: Optional[AIRuntime] = None) -> None:
        self.ai = ai_runtime or AIRuntime()

    def map_table_schema(self, agent_name: str, headers: List[str], sample_rows: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], str, int, float]:
        ai_res = self.ai.call_json(agent_name, TABLE_MAPPER_SYSTEM_PROMPT, json.dumps({"headers": headers, "sample_rows": sample_rows[:3]}, ensure_ascii=False))
        if not ai_res.used_fallback and isinstance(ai_res.parsed_json, dict):
            return ai_res.parsed_json, ai_res.model_id, ai_res.tokens_used, ai_res.latency_ms
        return _deterministic_header_mapping(headers), "deterministic_fallback", 0, 0.0

    def rows_to_source_records(self, config: SourceConfig, rows: List[Dict[str, Any]], locator_prefix: str, fetched_at_utc: str, source_url: str) -> List[SourceRecord]:
        if not rows:
            return []
        headers = list(rows[0].keys())
        mapping, model_id, tokens_used, latency_ms = self.map_table_schema(config.assigned_agent, headers, rows[:3])
        out: List[SourceRecord] = []
        for idx, row in enumerate(rows, 1):
            quote = json.dumps(row, ensure_ascii=False)
            crop = _nfc(row.get(mapping.get("crop_col") or "", ""))
            variety = _nfc(row.get(mapping.get("variety_col") or "", "")) or "General"
            district = _nfc(row.get(mapping.get("district_col") or "", ""))
            period = _nfc(row.get(mapping.get("time_period_col") or "", ""))
            loc = _nfc(row.get("locator", "")) or f"{locator_prefix};Row={idx}"
            val_col = mapping.get("raw_value_col")
            if val_col and row.get(val_col) is not None and str(row.get(val_col)).strip() != "":
                metric = _nfc(row.get(mapping.get("metric_name_col") or "", ""))
                raw_val = _nfc(row.get(val_col, "")).translate(ASSAMESE_DIGIT_MAP)
                raw_unit = _nfc(row.get(mapping.get("raw_unit_col") or "", ""))
                out.append(SourceRecord(source_id=config.source_id, source_url=source_url, source_type=config.source_group, extracting_agent=config.assigned_agent, locator=loc, crop_name=crop, variety_name=variety, district_raw=district, time_period=period, metric_name=metric, raw_value=raw_val, raw_unit=raw_unit, verbatim_quote=quote, fetched_at_utc=fetched_at_utc, llm_model_id=model_id, tokens_used=tokens_used if idx == 1 else 0, latency_ms=latency_ms if idx == 1 else 0.0, is_structured_table=True))
            else:
                for wm in mapping.get("wide_metric_cols") or []:
                    col_name = wm.get("col")
                    if not col_name or row.get(col_name) is None or str(row.get(col_name)).strip() == "":
                        continue
                    raw_val = _nfc(row.get(col_name, "")).translate(ASSAMESE_DIGIT_MAP)
                    raw_unit = _nfc(row.get(mapping.get("raw_unit_col") or "", "")) or _nfc(wm.get("unit", ""))
                    out.append(SourceRecord(source_id=config.source_id, source_url=source_url, source_type=config.source_group, extracting_agent=config.assigned_agent, locator=f"{loc};Col={col_name}", crop_name=crop, variety_name=variety, district_raw=district, time_period=period, metric_name=_nfc(wm.get("metric_name", "")), raw_value=raw_val, raw_unit=raw_unit, verbatim_quote=quote, fetched_at_utc=fetched_at_utc, llm_model_id=model_id, tokens_used=tokens_used if (idx == 1 and not out) else 0, latency_ms=latency_ms if (idx == 1 and not out) else 0.0, is_structured_table=True))
        return out

    def extract_unstructured_text(self, config: SourceConfig, text: str, locator_prefix: str, fetched_at_utc: str, source_url: str) -> List[SourceRecord]:
        norm_text = _nfc(text)
        if not norm_text:
            return []
        ai_res = self.ai.call_json(config.assigned_agent, UNSTRUCTURED_SYSTEM_PROMPT, f"Source URL: {source_url}\nSource Text:\n{norm_text[:12000]}")
        if not ai_res.used_fallback and isinstance(ai_res.parsed_json, dict) and isinstance(ai_res.parsed_json.get("records"), list):
            out: List[SourceRecord] = []
            for idx, item in enumerate(ai_res.parsed_json["records"], 1):
                if not isinstance(item, dict):
                    continue
                out.append(SourceRecord(source_id=config.source_id, source_url=source_url, source_type=config.source_group, extracting_agent=config.assigned_agent, locator=f"{locator_prefix};Span={idx}", crop_name=_nfc(item.get("crop_name", "")), variety_name=_nfc(item.get("variety_name", "")) or "General", district_raw=_nfc(item.get("district_raw", "")), time_period=_nfc(item.get("time_period", "")), metric_name=_nfc(item.get("metric_name", "")), raw_value=_nfc(item.get("raw_value", "")).translate(ASSAMESE_DIGIT_MAP), raw_unit=_nfc(item.get("raw_unit", "")), verbatim_quote=_nfc(item.get("verbatim_quote", "")), fetched_at_utc=fetched_at_utc, llm_model_id=ai_res.model_id, tokens_used=ai_res.tokens_used if idx == 1 else 0, latency_ms=ai_res.latency_ms if idx == 1 else 0.0))
            return out
        fallback_out: List[SourceRecord] = []
        for l_idx, ln in enumerate([l.strip() for l in norm_text.splitlines() if l.strip()], 1):
            if ":" not in ln and "=" not in ln:
                continue
            try:
                rec = AISemanticExtractor.extract_from_unstructured_text(ln, locator_prefix, l_idx, config.source_id, config.assigned_agent)
                fallback_out.append(SourceRecord(source_id=config.source_id, source_url=source_url, source_type=config.source_group, extracting_agent=config.assigned_agent, locator=f"{locator_prefix};Line={l_idx}", crop_name=rec["crop_name"], variety_name=rec["variety_name"], district_raw=rec["district_raw"], time_period=rec["time_period"], metric_name=rec["metric_name"], raw_value=rec["raw_value"], raw_unit=rec["raw_unit"], verbatim_quote=ln, fetched_at_utc=fetched_at_utc, llm_model_id="deterministic_fallback"))
            except ValueError:
                continue
        return fallback_out
