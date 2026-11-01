"""
Agent 1: Modality Classifier & Specialist Router (agent1_classifier.py)
Routes incoming sources/files/URLs to 'agent2_ingestion' (PDF/Web/CSV/TXT) or 'agent2b_live_gis' (Live Mandi & Web-GIS).
"""

import os
import re
from urllib.parse import urlparse
from typing import Dict, Any


class Agent1Classifier:
    MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

    GIS_KEYWORDS = ("wms", "geospatial", "gis", "bhoomi", "nesdr", "apartgis", "shapefile", "raster", "soil_ph", "lulc")
    MANDI_KEYWORDS = ("amiu", "mandi", "agmarknet", "modal_price", "modal_mandi_price", "quintal")

    @staticmethod
    def _peek_file_text(filepath: str, max_bytes: int = 4096) -> str:
        """Reads a small text sample from a local file for language and domain classification."""
        if not filepath or not os.path.isfile(filepath):
            return ""
        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".pdf", ".db", ".sqlite", ".png", ".jpg", ".tif", ".tiff"):
            return ""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_bytes)
        except OSError:
            return ""

    def classify_source(self, source_meta: Dict[str, Any]) -> Dict[str, Any]:
        filepath = str(source_meta.get("filepath", "") or source_meta.get("url", "")).strip()
        parsed_url = urlparse(filepath)
        is_url = parsed_url.scheme in ("http", "https")

        path_part = parsed_url.path if is_url else filepath
        ext = os.path.splitext(path_part)[1].lower()

        sgroup = str(source_meta.get("source_group", "") or "").strip()
        expected = str(source_meta.get("expected_agent", "") or "").strip()
        raw_text_sample = str(source_meta.get("raw_text_sample", "") or "")

        if not raw_text_sample and not is_url and filepath:
            raw_text_sample = self._peek_file_text(filepath)

        has_assamese = (
            bool(re.search(r"[\u0980-\u09FF]", raw_text_sample))
            or source_meta.get("language") == "as"
        )
        language = "as" if has_assamese else "en"

        combined_hint = f"{filepath} {sgroup} {raw_text_sample[:1000]}".lower()

        if (
            expected in ["agent2b_live_gis", "LiveMandi_Agent", "GeoSpatial_Agent"]
            or sgroup in ["Database_Dashboard", "Geospatial_GIS"]
            or any(k in combined_hint for k in self.GIS_KEYWORDS)
            or (is_url and any(k in combined_hint for k in self.MANDI_KEYWORDS))
        ):
            target_agent = "agent2b_live_gis"
        else:
            target_agent = "agent2_ingestion"

        if sgroup:
            source_type = sgroup
        elif target_agent == "agent2b_live_gis":
            source_type = "Geospatial_GIS" if any(k in combined_hint for k in self.GIS_KEYWORDS) else "Database_Dashboard"
        elif ext in [".pdf", ".csv"]:
            source_type = "Document_PDF"
        elif ext in [".html", ".htm", ".txt"] or is_url:
            source_type = "Web_Portal"
        else:
            source_type = "Document_PDF"

        modality = "URL" if (is_url and not ext) else (ext.lstrip(".").upper() if ext else "STRUCTURED_CASE")

        return {
            "routing_agent": "agent1_classifier",
            "target_agent": target_agent,
            "selected_tool": f"Tool:{target_agent}_Extractor",
            "source_type": source_type,
            "language": language,
            "modality": modality,
            "is_url": is_url,
            "tool_args_valid": bool(filepath or sgroup or expected),
            "ai_classifier_model": self.MODEL_ID,
        }