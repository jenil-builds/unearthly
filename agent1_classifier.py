"""
Agent 1: Modality Classifier & Specialist Router (agent1_classifier.py)
Routes incoming sources/files to 'agent2_ingestion' (PDF/Web/CSV/TXT) or 'agent2b_live_gis' (Live Mandi & Web-GIS).
"""

import os
import re
from typing import Dict, Any

class Agent1Classifier:
    MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"

    def classify_source(self, source_meta: Dict[str, Any]) -> Dict[str, Any]:
        filepath = str(source_meta.get("filepath", ""))
        ext = os.path.splitext(filepath)[1].lower()
        sgroup = str(source_meta.get("source_group", ""))
        expected = str(source_meta.get("expected_agent", ""))
        raw_text_sample = str(source_meta.get("raw_text_sample", ""))

        has_assamese = bool(re.search(r"[\u0980-\u09FF]", raw_text_sample)) or source_meta.get("language") == "as"
        language = "as" if has_assamese else "en"

        if expected in ["agent2b_live_gis", "LiveMandi_Agent", "GeoSpatial_Agent"] or sgroup in ["Database_Dashboard", "Geospatial_GIS"]:
            target_agent = "agent2b_live_gis"
        else:
            target_agent = "agent2_ingestion"

        if sgroup:
            source_type = sgroup
        elif ext in [".pdf", ".csv"]:
            source_type = "Document_PDF"
        elif ext in [".html", ".htm", ".txt"]:
            source_type = "Web_Portal"
        else:
            source_type = "Document_PDF"

        return {
            "routing_agent": "agent1_classifier",
            "target_agent": target_agent,
            "selected_tool": f"Tool:{target_agent}_Extractor",
            "source_type": source_type,
            "language": language,
            "modality": ext.lstrip(".").upper() if ext else "STRUCTURED_CASE",
            "tool_args_valid": True,
            "ai_classifier_model": self.MODEL_ID,
        }
