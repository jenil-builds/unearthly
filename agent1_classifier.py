"""
AGENT 1: agent1_classifier.py
=============================================================
ClassifierAgent — The first agent in the new 3-agent pipeline.

Responsibility:
    - Receives a raw source (URL, name, any metadata)
    - Classifies it into one of 4 types: PDF / Web / Web_Dynamic / Web_GIS
    - Decides which extraction tool Agent 2 should use
    - Passes enriched classification metadata forward in the pipeline state

Tool exposed:
    classify_source_tool(source_id, url, name, modality_hint) -> ClassificationResult
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────
# CLASSIFICATION RESULT SCHEMA
# ─────────────────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    source_id: str = Field(description="Unique source identifier e.g. SRC_01")
    classified_type: str = Field(
        description="One of: PDF | Web | Web_Dynamic | Web_GIS"
    )
    tool_to_use: str = Field(
        description="Extraction tool name to call"
    )
    agent_hint: str = Field(
        description="Specialist logic hint"
    )
    target_agent: str = Field(
        default="DocWeb_IngestionAgent",
        description="Assigned worker agent: DocWeb_IngestionAgent or LiveGIS_IngestionAgent"
    )
    confidence: float = Field(
        description="Classification confidence 0.0–1.0"
    )
    reason: str = Field(
        description="Short human-readable reason for the classification decision"
    )


# ─────────────────────────────────────────────────────────────────
# CLASSIFICATION RULES
# Rule-based → deterministic, no LLM cost, zero mis-routing risk
# ─────────────────────────────────────────────────────────────────

# URL keyword signals → type
_GIS_URL_SIGNALS    = ["gis", "wms", "geotiff", "geoportal", "nesdr", "astec",
                        "apartgis", "bhoomi", "web-gis", "remote-sensing"]
_MANDI_URL_SIGNALS  = ["amiu", "mandi", "agmarket", "market-price", "price-dashboard"]
_PDF_URL_SIGNALS    = [".pdf", "/pdf", "document", "swf_utility_folder", "portlet"]
_WEB_URL_SIGNALS    = ["kvk", "rkb", "aau.ac.in", "apeda", "diragri", "agro.html",
                        "factsheets", "pop.php", "information-services"]

# Modality hints (from source manifest)
_MODALITY_MAP = {
    "pdf":         ("PDF",         "extract_pdf_table_tool",             "TabularPDF", "DocWeb_IngestionAgent"),
    "web":         ("Web",         "fetch_clean_webpage_tool",           "WebPortal",  "DocWeb_IngestionAgent"),
    "web_dynamic": ("Web_Dynamic", "scrape_amiu_mandi_tool",             "LiveMandi",   "LiveGIS_IngestionAgent"),
    "web_gis":     ("Web_GIS",     "inspect_gis_portal_metadata_tool",   "GeoSpatial",  "LiveGIS_IngestionAgent"),
}


def classify_source_tool(
    source_id: str,
    url: str,
    name: str,
    modality_hint: Optional[str] = None
) -> ClassificationResult:
    """
    Tool used by ClassifierAgent.

    Classification priority:
      1. If modality_hint is given (from manifest) → trust it directly (confidence=1.0)
      2. Else → infer from URL keywords and name (confidence = 0.85 or 0.70)
    """

    # ── Step 1: Trust manifest modality if available ──────────────
    if modality_hint:
        key = modality_hint.strip().lower()
        if key in _MODALITY_MAP:
            ctype, tool, agent, target = _MODALITY_MAP[key]
            return ClassificationResult(
                source_id=source_id,
                classified_type=ctype,
                tool_to_use=tool,
                agent_hint=agent,
                target_agent=target,
                confidence=1.0,
                reason=f"Manifest modality='{modality_hint}' matched directly."
            )

    # ── Step 2: Infer from URL + name ─────────────────────────────
    url_lower  = url.lower()
    name_lower = name.lower()
    combined   = url_lower + " " + name_lower

    # Check GIS
    if any(sig in combined for sig in _GIS_URL_SIGNALS):
        return ClassificationResult(
            source_id=source_id,
            classified_type="Web_GIS",
            tool_to_use="inspect_gis_portal_metadata_tool",
            agent_hint="GeoSpatial",
            target_agent="LiveGIS_IngestionAgent",
            confidence=0.90,
            reason=f"URL/name contains GIS signal keywords."
        )

    # Check Mandi/Live Dashboard
    if any(sig in combined for sig in _MANDI_URL_SIGNALS):
        return ClassificationResult(
            source_id=source_id,
            classified_type="Web_Dynamic",
            tool_to_use="scrape_amiu_mandi_tool",
            agent_hint="LiveMandi",
            target_agent="LiveGIS_IngestionAgent",
            confidence=0.90,
            reason="URL/name contains mandi/market-price signal keywords."
        )

    # Check PDF
    if any(sig in combined for sig in _PDF_URL_SIGNALS):
        return ClassificationResult(
            source_id=source_id,
            classified_type="PDF",
            tool_to_use="extract_pdf_table_tool",
            agent_hint="TabularPDF",
            target_agent="DocWeb_IngestionAgent",
            confidence=0.85,
            reason="URL contains .pdf or document-path signals."
        )

    # Check Web Portal
    if any(sig in combined for sig in _WEB_URL_SIGNALS):
        return ClassificationResult(
            source_id=source_id,
            classified_type="Web",
            tool_to_use="fetch_clean_webpage_tool",
            agent_hint="WebPortal",
            target_agent="DocWeb_IngestionAgent",
            confidence=0.85,
            reason="URL/name matched known Assam web portal keywords."
        )

    # ── Step 3: File extension fallback ───────────────────────────
    if re.search(r"\.pdf($|\?)", url_lower):
        return ClassificationResult(
            source_id=source_id,
            classified_type="PDF",
            tool_to_use="extract_pdf_table_tool",
            agent_hint="TabularPDF",
            target_agent="DocWeb_IngestionAgent",
            confidence=0.75,
            reason="URL ends with .pdf extension."
        )

    # ── Step 4: Default fallback ───────────────────────────────────
    return ClassificationResult(
        source_id=source_id,
        classified_type="Web",
        tool_to_use="fetch_clean_webpage_tool",
        agent_hint="WebPortal",
        target_agent="DocWeb_IngestionAgent",
        confidence=0.50,
        reason="No strong signal found; defaulting to Web/WebPortal."
    )


# ─────────────────────────────────────────────────────────────────
# BATCH CLASSIFICATION (classify multiple sources at once)
# ─────────────────────────────────────────────────────────────────

def classify_all_sources(sources: List[Dict[str, Any]]) -> List[ClassificationResult]:
    """
    Classifies a full list of source manifest entries.

    Args:
        sources : List of dicts with keys: source_id, url, name, modality (optional)

    Returns:
        List of ClassificationResult objects — one per source, in order
    """
    results = []
    for src in sources:
        result = classify_source_tool(
            source_id=src.get("source_id", "UNKNOWN"),
            url=src.get("url", ""),
            name=src.get("name", src.get("source_name", "")),
            modality_hint=src.get("modality", src.get("source_group", None))
        )
        results.append(result)
    return results


# ─────────────────────────────────────────────────────────────────
# LANGGRAPH NODE FUNCTION
# ─────────────────────────────────────────────────────────────────

def classifier_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for ClassifierAgent (Agent 1).

    Reads:  state["source"]         → raw source dict from manifest
    Writes: state["classified_type"], state["tool_to_use"],
            state["agent_hint"],    state["classification_confidence"]
            state["trajectory"]     → appended with classification step
    """
    src = state["source"]

    result = classify_source_tool(
        source_id=src.get("source_id", "UNKNOWN"),
        url=src.get("url", ""),
        name=src.get("name", src.get("source_name", "")),
        modality_hint=src.get("modality", src.get("source_group", None))
    )

    state["classified_type"]           = result.classified_type
    state["tool_to_use"]               = result.tool_to_use
    state["agent_hint"]                = result.agent_hint
    state["target_agent"]              = result.target_agent
    state["classification_confidence"] = result.confidence
    state["trajectory"].append(
        f"ClassifierAgent -> {result.classified_type} "
        f"[target={result.target_agent}] "
        f"[tool={result.tool_to_use}] "
        f"[conf={result.confidence:.2f}]"
    )

    print(
        f"[ClassifierAgent] {result.source_id} | "
        f"Type={result.classified_type} | "
        f"Tool={result.tool_to_use} | "
        f"Confidence={result.confidence:.0%} | "
        f"Reason: {result.reason}"
    )

    return state


# ─────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from assam_config_and_db import ASSAM_SOURCES_MANIFEST

    print("\n" + "=" * 80)
    print("AGENT 1 — ClassifierAgent: Classifying all 15 sources")
    print("=" * 80)

    results = classify_all_sources(ASSAM_SOURCES_MANIFEST)

    print(f"\n{'Source ID':<10} {'Type':<15} {'Tool':<40} {'Conf':>5}  Reason")
    print("-" * 110)
    for r in results:
        print(
            f"{r.source_id:<10} {r.classified_type:<15} "
            f"{r.tool_to_use:<40} {r.confidence:>5.0%}  {r.reason}"
        )
    print(f"\n✅ Classified {len(results)}/15 sources successfully.")
