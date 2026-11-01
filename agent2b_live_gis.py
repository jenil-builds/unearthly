"""
Agent 2B: Live Market Intelligence & Geospatial Metadata Agent (agent2b_live_gis.py)
Handles Database_Dashboard (AMIU Live Mandi) and Geospatial_GIS (Web-GIS & Soil/Satellite) sources.
"""

import os
import csv
import json
from typing import List, Dict, Any
from agent2_ingestion import AISemanticExtractor, Agent2Ingestion, ASSAMESE_DIGIT_MAP


class Agent2BLiveGIS:
    MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

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
            "crop_name": r["crop_name"],
            "variety_name": r.get("variety_name", "General"),
            "district_raw": r.get("district_raw", "Jorhat"),
            "time_period": r.get("time_period", "2025-26"),
            "metric_name": r.get("metric_name", "Modal_Price"),
            "raw_value": str(r["raw_value"]).translate(ASSAMESE_DIGIT_MAP),
            "raw_unit": r["raw_unit"],
            "source_text_evidence": case_data.get("raw_source_snippet", str(r)),
        }]

    def ingest_file(self, filepath: str, source_type: str = "Database_Dashboard") -> List[Dict[str, Any]]:
        """Ingests direct files or URLs routed to Agent 2B (Live Mandi CSV/HTML/JSON or GIS metadata)."""
        if filepath.startswith(("http://", "https://")):
            helper = Agent2Ingestion()
            records = helper.ingest_url(filepath, source_id="SURPRISE_GIS_URL")
            for r in records:
                r["agent"] = "agent2b_live_gis"
                r["source_type"] = source_type
            return records

        ext = os.path.splitext(filepath)[1].lower()
        fname = os.path.basename(filepath)
        records: List[Dict[str, Any]] = []

        if ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return self.ingest_case_dict(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        records.extend(self.ingest_case_dict(item))
                return records

        elif ext == ".csv":
            with open(filepath, "r", encoding="utf-8") as f:
                for idx, row in enumerate(csv.DictReader(f), 1):
                    records.extend(
                        AISemanticExtractor.map_header_rows(
                            row, fname, f"File={fname};Row={idx}", "SURPRISE_GIS", source_type, "agent2b_live_gis"
                        )
                    )
            return records

        helper = Agent2Ingestion()
        records = helper.ingest_file(filepath)
        for r in records:
            r["agent"] = "agent2b_live_gis"
            r["source_type"] = source_type
        return records