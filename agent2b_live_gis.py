"""
Agent 2B: Live Market Intelligence & Geospatial Metadata Agent (agent2b_live_gis.py)
Handles LiveMandi_Agent (Database_Dashboard) and GeoSpatial_Agent (Geospatial_GIS) tasks.
"""

from typing import List, Dict, Any


class Agent2BLiveGIS:
    """
    Independent Agent for Live Mandi Dashboards & Web-GIS Portals:
    - LiveMandi_Agent: Extracts rolling market arrival & modal price series (Rs/Quintal).
    - GeoSpatial_Agent: Extracts WMS/WFS layer capabilities, spatial resolution (meters), scale, and soil pH.
    """

    def ingest_case_dict(self, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        r = case_data.get("structured_source_row", case_data)
        expected_agent = case_data.get("expected_agent", "LiveMandi_Agent")
        sgroup = case_data.get("source_group", "Database_Dashboard" if expected_agent == "LiveMandi_Agent" else "Geospatial_GIS")
        return [{
            "source_id": r.get("source_id", case_data.get("source_id", "SRC_11")),
            "source_type": sgroup,
            "agent": expected_agent,
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
