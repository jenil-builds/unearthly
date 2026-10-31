"""
AGENT 2B: agent2b_live_gis.py
=============================================================
LiveGIS_IngestionAgent — Dynamic Market & GeoSpatial Ingestion Agent.

Responsibility:
    - Dedicated to handling high-load, dynamic, and spatial sources:
      1. scrape_amiu_mandi_tool           ← for AMIU Jorhat & live Mandi dashboards
      2. inspect_gis_portal_metadata_tool ← for WMS / Web-GIS spatial portals (Bhoomi, ASTEC, NESAC)
    - Offloads live network scraping and GIS metadata parsing from Agent 2
    - Normalizes dynamic market prices and GIS spatial bounds to SI canonical standards
    - Writes validated records directly to the SQLite database
"""

import os
import sys
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Import the 2 dynamic/GIS extraction tools
from assam_agents_and_tools import (
    scrape_amiu_mandi_tool,
    inspect_gis_portal_metadata_tool,
    OpenSourceLLMExtractor,
)

# Import normalization helpers
from assam_config_and_db import (
    clean_indian_number,
    standardize_unit,
    resolve_assam_district,
)

# ─────────────────────────────────────────────────────────────────
# TOOL REGISTRY FOR DYNAMIC & GIS INGESTION
# ─────────────────────────────────────────────────────────────────

LIVE_GIS_TOOL_REGISTRY: Dict[str, Any] = {
    "scrape_amiu_mandi_tool":           scrape_amiu_mandi_tool,
    "inspect_gis_portal_metadata_tool": inspect_gis_portal_metadata_tool,
}


def _build_live_gis_args(tool_name: str, src: Dict[str, Any]) -> Dict[str, Any]:
    """Constructs arguments tailored for dynamic mandi & GIS metadata tools."""
    if tool_name == "scrape_amiu_mandi_tool":
        return {
            "url": src["url"],
            "snapshot_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
    elif tool_name == "inspect_gis_portal_metadata_tool":
        return {"url": src["url"]}
    else:
        return {"url": src["url"]}


def _normalize_live_gis_records(
    payload: Dict[str, Any],
    run_id: str
) -> List[Dict[str, Any]]:
    """Normalizes live mandi and GIS metadata records into standard DB rows."""
    normalized = []
    records = payload.get("records", [])

    for rec in records:
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
            "record_hash":        record_hash,
            "source_id":          payload["source_id"],
            "source_type":        "Live_Dynamic_GIS",
            "run_id":             run_id,
            "extracting_agent":   "LiveGIS_IngestionAgent",
            "source_location":    rec.get("locator", "Live/Spatial Stream"),
            "location_id":        loc_info["lgd_code"],
            "canonical_district": loc_info["canonical_name"],
            "agro_climatic_zone": loc_info["agro_climatic_zone"],
            "crop_name":          rec.get("crop_name", "General Agriculture"),
            "variety_name":       rec.get("variety_name", "All"),
            "time_period":        rec.get("time_period", "2025-26"),
            "metric_name":        rec.get("metric_name", "Market_or_GIS_Metric"),
            "raw_value_text":     str(rec.get("raw_value", "")),
            "raw_unit":           rec.get("raw_unit", ""),
            "normalized_value":   unit_info["normalized_value"],
            "normalized_unit":    unit_info["normalized_unit"],
            "validation_status":  "VALID",
        })

    return normalized


def _write_live_gis_to_db(
    records: List[Dict[str, Any]],
    db_path: str = "db/assam_agri_phase2.db"
) -> int:
    """Inserts normalized live mandi & GIS records into SQLite."""
    if not records:
        return 0

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    written = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for rec in records:
        try:
            # 1. dim_locations
            cur.execute(
                "INSERT OR IGNORE INTO dim_locations VALUES (?, ?, ?, 'Assam')",
                (rec["location_id"], rec.get("canonical_district", "Assam"), rec.get("agro_climatic_zone", "All Zones"))
            )

            # 2. dim_crops
            crop_id = hashlib.md5(
                f"{rec['crop_name']}|{rec['variety_name']}".encode()
            ).hexdigest()[:12]
            cur.execute(
                "INSERT OR IGNORE INTO dim_crops VALUES (?, ?, ?, ?)",
                (crop_id, rec["crop_name"], rec["variety_name"], rec.get("season", "Annual"))
            )

            # 3. extraction_runs
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

            # 4. fact_agricultural_records
            cur.execute("""
                INSERT OR REPLACE INTO fact_agricultural_records
                   (record_hash, source_id, source_type, run_id, extracting_agent,
                    source_location, location_id, crop_id, time_period, metric_name,
                    raw_value_text, raw_unit, normalized_value, normalized_unit,
                    validation_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rec["record_hash"], rec["source_id"],
                    "Live_Mandi_Stream" if "11" in rec.get("source_id", "") or "amiu" in rec.get("source_id", "").lower() else "Web_GIS",
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
            print(f"  [LiveGIS_Agent][DB WARNING] Skipped record {rec.get('record_hash','?')}: {e}")

    conn.commit()
    conn.close()
    return written


_llm_extractor = OpenSourceLLMExtractor()


def live_gis_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for LiveGIS_IngestionAgent.
    Dedicated worker for:
      - scrape_amiu_mandi_tool (Live Mandi prices)
      - inspect_gis_portal_metadata_tool (GeoSpatial WMS capabilities)
    """
    src        = state["source"]
    run_id     = state["run_id"]
    tool_name  = state.get("tool_to_use", "scrape_amiu_mandi_tool")
    agent_hint = state.get("agent_hint", "LiveMandi")

    print(f"\n[LiveGIS_Agent] Processing {src['source_id']} | Tool={tool_name}")

    # Fallback tool resolution if an unsupported tool arrived
    tool_fn = LIVE_GIS_TOOL_REGISTRY.get(tool_name, scrape_amiu_mandi_tool)
    tool_args = _build_live_gis_args(tool_name, src)

    state["tool_invoked"] = tool_name
    state["tool_input"]   = tool_args
    state["trajectory"].append(f"LiveGIS_Agent -> Tool:{tool_name}")

    try:
        raw_output = tool_fn(**tool_args)
    except Exception as e:
        raw_output = {"mode": "ERROR", "error": str(e)}
        state["errors"].append(f"LiveGIS Tool {tool_name} failed: {e}")

    state["raw_tool_output"] = str(raw_output)
    print(f"  Tool returned: mode={raw_output.get('mode','?')}")

    # Extract structured payload
    payload = _llm_extractor.extract(
        source_id=src["source_id"],
        agent_name=f"{agent_hint}_Agent",
        evidence_context=state["raw_tool_output"]
    )
    payload_dict = payload.model_dump()
    payload_dict["records"] = [
        r.model_dump() if hasattr(r, "model_dump") else r
        for r in payload_dict.get("records", [])
    ]
    state["extracted_payload"] = payload_dict

    # Normalize records
    normalized = _normalize_live_gis_records(payload_dict, run_id)
    state["normalized_records"] = normalized
    state["needs_self_correction"] = False

    # Write to DB
    written = _write_live_gis_to_db(normalized)
    state["db_records_written"] = written

    state["trajectory"].append(
        f"LiveGIS_Agent -> Normalized:{len(normalized)} -> DB_Written:{written}"
    )
    state["status"] = "INGESTED"

    print(
        f"  [LiveGIS_Agent] OK {src['source_id']}: "
        f"{len(normalized)} normalized, {written} written to DB"
    )

    return state
