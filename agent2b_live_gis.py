"""
Agent 2B: Live Market Intelligence & Geospatial Metadata Agent (agent2b_live_gis.py)
Handles Database_Dashboard (AMIU Live Mandi) and Geospatial_GIS (Web-GIS & Soil/Satellite) sources.
"""

from typing import List, Dict, Any

class Agent2BLiveGIS:
    MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"

    def ingest_case_dict(self, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        r = case_data.get("structured_source_row", case_data)
        sgroup = case_data.get("source_group", "Database_Dashboard")
        required_fields = (
            "crop_name",
            "raw_value",
            "raw_unit",
        )
        missing_fields = [
            field for field in required_fields
            if field not in r or r[field] is None or not str(r[field]).strip()
        ]

        if missing_fields:
            raise ValueError(
                f"Missing required extraction field(s): {', '.join(missing_fields)}"
            )

        return [{
            "source_id": r.get("source_id", case_data.get("source_id", "SRC_11")),
            "source_type": sgroup,
            "agent": "agent2b_live_gis",
            "locator": r.get("locator", "Dashboard=AMIU;Row=1"),
            "crop_name": r.get("crop_name", "Rice (Paddy)"),
            "variety_name": r.get("variety_name", "General"),
            "district_raw": r.get("district_raw", "Jorhat"),
            "time_period": r.get("time_period", "2025-26"),
            "metric_name": r.get("metric_name", "Modal_Price"),
            "raw_value": str(r.get("raw_value", "2250")),
            "raw_unit": r.get("raw_unit", "Rs/Quintal"),
            "source_text_evidence": case_data.get("raw_source_snippet", str(r)),
        }]
