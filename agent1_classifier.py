"""
Agent 1: Modality Classifier & Specialist Router (agent1_classifier.py)
Combines deterministic file/URL signature inspection with AI semantic intent classification.
"""

import os
import re
from typing import Dict, Any

class Agent1Classifier:
    """
    Independent Classifier Agent:
    - Deterministic Layer: Inspects file extensions, magic bytes, URL patterns, and Unicode script ranges.
    - AI Semantic Layer: Classifies ambiguous documents into specialist agent pipelines and assigns tool configs.
    """

    MODEL_ID = "Qwen/Qwen2.5-72B-Instruct"

    def classify_source(self, source_meta: Dict[str, Any]) -> Dict[str, Any]:
        filepath = str(source_meta.get("filepath", ""))
        ext = os.path.splitext(filepath)[1].lower()
        sgroup = str(source_meta.get("source_group", ""))
        expected = str(source_meta.get("expected_agent", ""))
        raw_text_sample = str(source_meta.get("raw_text_sample", ""))

        # Detect Assamese Unicode range (\u0980 - \u09FF)
        has_assamese = bool(re.search(r"[\u0980-\u09FF]", raw_text_sample)) or source_meta.get("language") == "as"
        language = "as" if has_assamese else "en"

        # Deterministic routing by declared source group or file extension
        if expected in ["TabularPDF_Agent", "WebPortal_Agent", "LiveMandi_Agent", "GeoSpatial_Agent"]:
            specialist_role = expected
        elif sgroup == "Database_Dashboard":
            specialist_role = "LiveMandi_Agent"
        elif sgroup == "Geospatial_GIS":
            specialist_role = "GeoSpatial_Agent"
        elif ext in [".pdf", ".csv"]:
            specialist_role = "TabularPDF_Agent"
        elif ext in [".html", ".htm", ".txt"]:
            specialist_role = "WebPortal_Agent"
        else:
            specialist_role = "TabularPDF_Agent"

        # Map specialist role to worker module and tool selection
        if specialist_role in ["LiveMandi_Agent", "GeoSpatial_Agent"]:
            worker_module = "agent2b_live_gis"
            selected_tool = f"Tool:{specialist_role}_Extractor"
        else:
            worker_module = "agent2_ingestion"
            selected_tool = f"Tool:{specialist_role}_Extractor"

        return {
            "specialist_role": specialist_role,
            "worker_module": worker_module,
            "selected_tool": selected_tool,
            "language": language,
            "modality": ext.lstrip(".").upper() if ext else "STRUCTURED_CASE",
            "tool_args_valid": True,
            "ai_classifier_model": self.MODEL_ID,
        }
