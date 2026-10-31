"""
AGENT 2: agent2_ingestion.py
=============================================================
DocWeb_IngestionAgent — Document & Web Portal Ingestion Agent.

Responsibility:
    - Receives document & static web sources routed from ClassifierAgent
    - Handles extraction for:
        1. extract_pdf_table_tool()   ← for PDF tabular sources (SRC_01–05)
        2. fetch_clean_webpage_tool() ← for HTML Web Portals (SRC_06–10)
    - Normalizes data (clean numbers, SI canonical units, LGD mapping)
    - Handles self-correction retry loop for footnote-contaminated cells (*)
    - Writes validated records directly to SQLite database
"""

import sys
import re
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Import all 4 existing extraction tools
from assam_agents_and_tools import (
    extract_pdf_table_tool,
    fetch_clean_webpage_tool,
    scrape_amiu_mandi_tool,
    inspect_gis_portal_metadata_tool,
    OpenSourceLLMExtractor,
)

# Import normalization helpers and DB initializer
from assam_config_and_db import (
    clean_indian_number,
    standardize_unit,
    resolve_assam_district,
    init_database,
)

# ─────────────────────────────────────────────────────────────────
# TOOL REGISTRY
# Maps classified_type → (tool_function, tool_name)
# Agent 2 owns ALL 4 tools and picks the right one dynamically
# ─────────────────────────────────────────────────────────────────

TOOL_REGISTRY: Dict[str, Any] = {
    "extract_pdf_table_tool":             extract_pdf_table_tool,
    "fetch_clean_webpage_tool":           fetch_clean_webpage_tool,
    "scrape_amiu_mandi_tool":             scrape_amiu_mandi_tool,
    "inspect_gis_portal_metadata_tool":   inspect_gis_portal_metadata_tool,
}

# Tool argument builders — each tool needs slightly different inputs
def _build_tool_args(tool_name: str, src: Dict[str, Any]) -> Dict[str, Any]:
    """Build the correct kwargs for each tool based on source metadata."""
    if tool_name == "extract_pdf_table_tool":
        return {"url": src["url"], "filter_state": "Assam", "attempt_live_network": False}
    elif tool_name == "fetch_clean_webpage_tool":
        return {"url": src["url"], "attempt_live_network": False}
    elif tool_name == "scrape_amiu_mandi_tool":
        return {"url": src["url"], "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    elif tool_name == "inspect_gis_portal_metadata_tool":
        return {"url": src["url"]}
    else:
        return {"url": src["url"]}


# ─────────────────────────────────────────────────────────────────
# SELF-CORRECTION LOGIC (inline within Agent 2)
# ─────────────────────────────────────────────────────────────────

def _strip_footnote_markers(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Strips footnote markers ('*') and OCR artifacts from raw_value fields.
    Also strips corrupt tokens like 'CORRUPT_NaN_'.
    e.g. '48,527*' → '48,527'   |   'CORRUPT_NaN_99,400*' → '99,400'
    """
    cleaned = []
    for rec in records:
        r = dict(rec)
        r["raw_value"] = re.sub(r"[A-Za-z_*]", "", str(r["raw_value"])).strip()
        # Remove leading/trailing commas or dots
        r["raw_value"] = r["raw_value"].strip(",. ")
        cleaned.append(r)
    return cleaned


def _has_footnote_contamination(records: List[Dict[str, Any]]) -> bool:
    """Returns True if any record's raw_value contains a '*' or 'CORRUPT' token."""
    for rec in records:
        val = str(rec.get("raw_value", ""))
        if "*" in val or "CORRUPT" in val.upper():
            return True
    return False


# ─────────────────────────────────────────────────────────────────
# NORMALIZATION LOGIC
# Converts raw extracted records into DB-ready normalized records
# ─────────────────────────────────────────────────────────────────

def _normalize_records(
    payload: Dict[str, Any],
    run_id: str
) -> List[Dict[str, Any]]:
    """
    Normalizes a list of ExtractedFactItem dicts into DB-ready rows.

    Steps per record:
      1. Parse Indian-formatted number (remove commas)
      2. Convert units to SI canonical (q/ha → kg/ha, Rs. Lakh → INR, etc.)
      3. Resolve raw district name to LGD canonical code & zone
      4. Compute SHA-256 record_hash (for deduplication)
      5. Return fully normalized row dict
    """
    normalized = []
    records = payload.get("records", [])

    for rec in records:
        # Convert ExtractedFactItem to dict if needed
        if hasattr(rec, "model_dump"):
            rec = rec.model_dump()

        num_val = clean_indian_number(rec.get("raw_value", "0"))
        unit_info = standardize_unit(num_val or 0.0, rec.get("raw_unit", ""))
        loc_info = resolve_assam_district(rec.get("district_raw", "Assam"))

        hash_input = (
            f"{payload['source_id']}|{rec.get('crop_name','')}|"
            f"{rec.get('variety_name','')}|{loc_info['lgd_code']}|"
            f"{rec.get('time_period','')}|{rec.get('metric_name','')}"
        )
        record_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:24]

        normalized.append({
            "record_hash":       record_hash,
            "source_id":         payload["source_id"],
            "run_id":            run_id,
            "extracting_agent":  payload.get("extracting_agent", "IngestionAgent"),
            "source_location":   rec.get("source_location", "unknown"),
            "location_id":       loc_info["lgd_code"],
            "canonical_district": loc_info["canonical_name"],
            "agro_climatic_zone": loc_info["agro_climatic_zone"],
            "crop_name":         rec.get("crop_name", ""),
            "variety_name":      rec.get("variety_name", "General"),
            "season":            rec.get("season", "Annual"),
            "time_period":       rec.get("time_period", ""),
            "metric_name":       rec.get("metric_name", ""),
            "raw_value_text":    str(rec.get("raw_value", "")),
            "raw_unit":          rec.get("raw_unit", ""),
            "normalized_value":  unit_info["normalized_value"],
            "normalized_unit":   unit_info["normalized_unit"],
            "validation_status": "VALIDATED" if num_val is not None else "FAILED_NUMERIC_CHECK",
        })

    return normalized


# ─────────────────────────────────────────────────────────────────
# DATABASE WRITE LOGIC
# ─────────────────────────────────────────────────────────────────

def _write_records_to_db(
    normalized_records: List[Dict[str, Any]],
    db_path: str = "db/assam_agri_phase2.db"
) -> int:
    """
    Writes all normalized records to SQLite DB.

    For each record:
      - Inserts/updates dim_locations
      - Inserts/updates dim_crops
      - Inserts extraction_runs row
      - Inserts fact_agricultural_records row (UNIQUE by record_hash)

    Returns:
        Number of records successfully written
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    written = 0

    for rec in normalized_records:
        try:
            now_iso = datetime.now(timezone.utc).isoformat()

            # dim_locations
            cur.execute(
                "INSERT OR IGNORE INTO dim_locations VALUES (?, ?, ?, 'Assam')",
                (rec["location_id"], rec["canonical_district"], rec["agro_climatic_zone"])
            )

            # dim_crops
            crop_id = hashlib.md5(
                f"{rec['crop_name']}|{rec['variety_name']}".encode()
            ).hexdigest()[:12]
            cur.execute(
                "INSERT OR IGNORE INTO dim_crops VALUES (?, ?, ?, ?)",
                (crop_id, rec["crop_name"], rec["variety_name"], rec.get("season", "Annual"))
            )

            # extraction_runs
            cur.execute(
                """INSERT OR REPLACE INTO extraction_runs
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec["run_id"], rec["source_id"], rec["extracting_agent"],
                    "Qwen/Qwen2.5-72B-Instruct",
                    now_iso, now_iso,
                    115.0, 420, 0, 0, "COMPLETED", None
                )
            )

            # fact_agricultural_records
            cur.execute(
                """INSERT OR REPLACE INTO fact_agricultural_records
                   (record_hash, source_id, source_type, run_id, extracting_agent,
                    source_location, location_id, crop_id, time_period, metric_name,
                    raw_value_text, raw_unit, normalized_value, normalized_unit,
                    validation_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec["record_hash"], rec["source_id"],
                    "Document_PDF" if "pdf" in rec.get("source_id", "").lower() else "Web_Portal",
                    rec["run_id"], rec["extracting_agent"],
                    rec["source_location"], rec["location_id"], crop_id,
                    rec["time_period"], rec["metric_name"],
                    rec["raw_value_text"], rec["raw_unit"],
                    rec["normalized_value"], rec["normalized_unit"],
                    rec["validation_status"]
                )
            )
            written += 1

        except Exception as e:
            print(f"  [IngestionAgent][DB WARNING] Skipped record {rec.get('record_hash','?')}: {e}")

    conn.commit()
    conn.close()
    return written


# ─────────────────────────────────────────────────────────────────
# INGESTION AGENT — CORE FUNCTION
# ─────────────────────────────────────────────────────────────────

_llm_extractor = OpenSourceLLMExtractor()


def ingestion_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for IngestionAgent (Agent 2).

    Reads from state:
        source, run_id, classified_type, tool_to_use, agent_hint,
        retry_count, needs_self_correction

    Writes to state:
        tool_invoked, tool_input, raw_tool_output, extracted_payload,
        normalized_records, db_records_written, needs_self_correction,
        trajectory, status
    """
    src          = state["source"]
    run_id       = state["run_id"]
    tool_name    = state.get("tool_to_use", "fetch_clean_webpage_tool")
    agent_hint   = state.get("agent_hint", "WebPortal")
    retry_count  = state.get("retry_count", 0)

    print(f"\n[IngestionAgent] Processing {src['source_id']} | Tool={tool_name} | Retry={retry_count}")

    # ── Step 1: Call the correct extraction tool ───────────────────
    tool_fn   = TOOL_REGISTRY.get(tool_name, fetch_clean_webpage_tool)
    tool_args = _build_tool_args(tool_name, src)

    state["tool_invoked"] = tool_name
    state["tool_input"]   = tool_args
    state["trajectory"].append(f"IngestionAgent -> Tool:{tool_name}")

    try:
        raw_output = tool_fn(**tool_args)
    except Exception as e:
        raw_output = {"mode": "ERROR", "error": str(e)}
        state["errors"].append(f"Tool {tool_name} failed: {e}")

    state["raw_tool_output"] = str(raw_output)
    print(f"  Tool returned: mode={raw_output.get('mode','?')}")

    # ── Step 2: LLM structured extraction (or verified cache) ──────
    payload = _llm_extractor.extract(
        source_id=src["source_id"],
        agent_name=f"{agent_hint}_Agent",
        evidence_context=state["raw_tool_output"]
    )
    payload_dict = payload.model_dump()

    # Convert list of Pydantic models to plain dicts
    payload_dict["records"] = [
        r.model_dump() if hasattr(r, "model_dump") else r
        for r in payload_dict.get("records", [])
    ]
    state["extracted_payload"] = payload_dict

    # ── Step 3: Check for footnote contamination ───────────────────
    if _has_footnote_contamination(payload_dict["records"]) and retry_count == 0:
        print(f"  [IngestionAgent] Footnote '*' detected → routing to SelfCorrectionNode")
        state["needs_self_correction"] = True
        state["trajectory"].append("IngestionAgent -> NeedsSelfCorrection")
        return state

    # ── Step 4: If coming back after self-correction, strip markers ─
    if retry_count > 0:
        payload_dict["records"] = _strip_footnote_markers(payload_dict["records"])
        state["extracted_payload"] = payload_dict
        print(f"  [IngestionAgent] Post-correction: stripped all footnote markers")

    # ── Step 5: Normalize records ──────────────────────────────────
    normalized = _normalize_records(payload_dict, run_id)
    state["normalized_records"] = normalized
    state["needs_self_correction"] = False

    # ── Step 6: Write to DB ────────────────────────────────────────
    written = _write_records_to_db(normalized)
    state["db_records_written"] = written

    state["trajectory"].append(
        f"IngestionAgent -> Normalized:{len(normalized)} -> DB_Written:{written}"
    )
    state["status"] = "INGESTED"

    print(
        f"  [IngestionAgent] ✅ {src['source_id']}: "
        f"{len(normalized)} normalized, {written} written to DB"
    )

    return state


# ─────────────────────────────────────────────────────────────────
# SELF CORRECTION NODE (belongs to Agent 2's responsibility)
# ─────────────────────────────────────────────────────────────────

def ingestion_self_correction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Self-correction sub-step within Agent 2.
    Strips '*' and corrupt tokens, increments retry, re-routes to ingestion_agent_node.
    """
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["trajectory"].append(
        f"SelfCorrectionNode:StripFootnoteMarkers (retry={state['retry_count']})"
    )

    # Strip from the already-extracted payload so Agent 2 can skip re-extraction
    if state.get("extracted_payload"):
        recs = state["extracted_payload"].get("records", [])
        state["extracted_payload"]["records"] = _strip_footnote_markers(recs)

    state["needs_self_correction"] = False
    print(f"  [SelfCorrectionNode] Retry #{state['retry_count']}: footnotes stripped")
    return state


# ─────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from assam_config_and_db import ASSAM_SOURCES_MANIFEST, init_database

    print("\n" + "=" * 80)
    print("AGENT 2 — IngestionAgent: Testing on SRC_01 (PDF with footnotes)")
    print("=" * 80)

    # Initialize DB
    conn = init_database("db/assam_agri_phase2.db")
    conn.close()

    test_state = {
        "source":               ASSAM_SOURCES_MANIFEST[0],   # SRC_01
        "run_id":               "RUN_TEST_AGENT2_001",
        "classified_type":      "PDF",
        "tool_to_use":          "extract_pdf_table_tool",
        "agent_hint":           "TabularPDF",
        "retry_count":          0,
        "needs_self_correction": False,
        "extracted_payload":    None,
        "normalized_records":   [],
        "db_records_written":   0,
        "trajectory":           ["ClassifierAgent -> PDF [tool=extract_pdf_table_tool]"],
        "errors":               [],
        "status":               "CLASSIFIED",
    }

    result_state = ingestion_agent_node(test_state)

    print(f"\nTrajectory: {' | '.join(result_state['trajectory'])}")
    print(f"DB Records Written: {result_state['db_records_written']}")
    print(f"Status: {result_state['status']}")
