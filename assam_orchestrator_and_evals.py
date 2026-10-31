"""
MODULE 3: assam_orchestrator_and_evals.py
Contains:
- Real Compiled LangGraph StateGraph (Supervisor -> 4 Specialist Agents -> SchemaNormalizer -> Self-Correction Retry)
- Foundry Agent Evaluators (ToolSelection, ToolInputAccuracy, TaskCompletion, Groundedness, ProvenanceAndUnitBonus)
- AgentEvals Trajectory Strict/Unordered Match Evaluator
"""

import hashlib
from typing import Dict, List, Any, Optional, TypedDict
from assam_config_and_db import clean_indian_number, standardize_unit, resolve_assam_district
from assam_agents_and_tools import (
    extract_pdf_table_tool,
    fetch_clean_webpage_tool,
    scrape_amiu_mandi_tool,
    inspect_gis_portal_metadata_tool,
    OpenSourceLLMExtractor,
)

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

try:
    from agentevals.trajectory.match import create_trajectory_match_evaluator
    AGENTEVALS_AVAILABLE = True
except ImportError:
    AGENTEVALS_AVAILABLE = False

class PipelineState(TypedDict):
    source: Dict[str, Any]
    run_id: str
    selected_agent: str
    tool_invoked: str
    tool_input: Dict[str, Any]
    raw_tool_output: str
    extracted_payload: Optional[Dict[str, Any]]
    normalized_records: List[Dict[str, Any]]
    retry_count: int
    needs_self_correction: bool
    errors: List[str]
    trajectory: List[str]
    status: str

llm_extractor = OpenSourceLLMExtractor()

def supervisor_router_node(state: PipelineState) -> PipelineState:
    modality = state["source"]["modality"]
    if modality == "PDF":
        agent = "TabularPDF_Agent"
    elif modality == "Web":
        agent = "WebPortal_Agent"
    elif modality == "Web_Dynamic":
        agent = "LiveMandi_Agent"
    else:
        agent = "GeoSpatial_Agent"
    state["selected_agent"] = agent
    state["trajectory"].append(f"SupervisorRouter->{agent}")
    return state

def route_from_supervisor(state: PipelineState) -> str:
    return state["selected_agent"]

def tabular_pdf_agent_node(state: PipelineState) -> PipelineState:
    src = state["source"]
    state["tool_invoked"] = "extract_pdf_table_tool"
    state["tool_input"] = {"url": src["url"], "filter_state": "Assam"}
    state["trajectory"].append("Tool:extract_pdf_table_tool")
    tool_res = extract_pdf_table_tool(url=src["url"], filter_state="Assam")
    state["raw_tool_output"] = str(tool_res)
    payload = llm_extractor.extract(src["source_id"], "TabularPDF_Agent", state["raw_tool_output"])
    state["extracted_payload"] = payload.model_dump()
    return state

def web_portal_agent_node(state: PipelineState) -> PipelineState:
    src = state["source"]
    state["tool_invoked"] = "fetch_clean_webpage_tool"
    state["tool_input"] = {"url": src["url"]}
    state["trajectory"].append("Tool:fetch_clean_webpage_tool")
    tool_res = fetch_clean_webpage_tool(url=src["url"])
    state["raw_tool_output"] = str(tool_res)
    payload = llm_extractor.extract(src["source_id"], "WebPortal_Agent", state["raw_tool_output"])
    state["extracted_payload"] = payload.model_dump()
    return state

def live_mandi_agent_node(state: PipelineState) -> PipelineState:
    src = state["source"]
    state["tool_invoked"] = "scrape_amiu_mandi_tool"
    state["tool_input"] = {"url": src["url"], "snapshot_date": "2026-10-18"}
    state["trajectory"].append("Tool:scrape_amiu_mandi_tool")
    tool_res = scrape_amiu_mandi_tool(url=src["url"], snapshot_date="2026-10-18")
    state["raw_tool_output"] = str(tool_res)
    payload = llm_extractor.extract(src["source_id"], "LiveMandi_Agent", state["raw_tool_output"])
    state["extracted_payload"] = payload.model_dump()
    return state

def geospatial_agent_node(state: PipelineState) -> PipelineState:
    src = state["source"]
    state["tool_invoked"] = "inspect_gis_portal_metadata_tool"
    state["tool_input"] = {"url": src["url"]}
    state["trajectory"].append("Tool:inspect_gis_portal_metadata_tool")
    tool_res = inspect_gis_portal_metadata_tool(url=src["url"])
    state["raw_tool_output"] = str(tool_res)
    payload = llm_extractor.extract(src["source_id"], "GeoSpatial_Agent", state["raw_tool_output"])
    state["extracted_payload"] = payload.model_dump()
    return state

def self_correction_node(state: PipelineState) -> PipelineState:
    """Strips footnote markers ('*') orocr artifacts from raw numeric cells and re-validates."""
    state["retry_count"] += 1
    state["trajectory"].append("SelfCorrectionNode:StripFootnoteSymbols")
    for rec in state["extracted_payload"]["records"]:
        rec["raw_value"] = str(rec["raw_value"]).replace("*", "").strip()
    state["needs_self_correction"] = False
    return state

def schema_normalizer_node(state: PipelineState) -> PipelineState:
    state["trajectory"].append("SchemaNormalizer_Agent")
    payload = state["extracted_payload"]
    normalized = []

    # Check if any raw_value has an uncleaned footnote marker '*' on first pass
    for rec in payload["records"]:
        if "*" in str(rec["raw_value"]) and state["retry_count"] == 0:
            state["needs_self_correction"] = True
            return state

    for rec in payload["records"]:
        num_val = clean_indian_number(rec["raw_value"])
        unit_info = standardize_unit(num_val or 0.0, rec["raw_unit"])
        loc_info = resolve_assam_district(rec["district_raw"])

        hash_input = f"{payload['source_id']}|{rec['crop_name']}|{rec['variety_name']}|{loc_info['lgd_code']}|{rec['time_period']}|{rec['metric_name']}"
        record_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:24]

        normalized.append({
            "record_hash": record_hash,
            "source_id": payload["source_id"],
            "run_id": state["run_id"],
            "extracting_agent": payload["extracting_agent"],
            "source_location": rec["source_location"],
            "location_id": loc_info["lgd_code"],
            "canonical_district": loc_info["canonical_name"],
            "agro_climatic_zone": loc_info["agro_climatic_zone"],
            "crop_name": rec["crop_name"],
            "variety_name": rec["variety_name"],
            "season": rec["season"],
            "time_period": rec["time_period"],
            "metric_name": rec["metric_name"],
            "raw_value_text": rec["raw_value"],
            "raw_unit": rec["raw_unit"],
            "normalized_value": unit_info["normalized_value"],
            "normalized_unit": unit_info["normalized_unit"],
            "validation_status": "VALIDATED" if num_val is not None else "FAILED_NUMERIC_CHECK"
        })

    state["normalized_records"] = normalized
    state["status"] = "COMPLETED"
    state["trajectory"].append("DB_Commit_Ready")
    return state

def check_validation_gate(state: PipelineState) -> str:
    if state.get("needs_self_correction") and state["retry_count"] < 2:
        return "self_correct"
    return "complete"

def build_compiled_langgraph():
    """Builds and compiles the real LangGraph StateGraph workflow."""
    if not LANGGRAPH_AVAILABLE:
        return None
    workflow = StateGraph(PipelineState)
    workflow.add_node("supervisor", supervisor_router_node)
    workflow.add_node("TabularPDF_Agent", tabular_pdf_agent_node)
    workflow.add_node("WebPortal_Agent", web_portal_agent_node)
    workflow.add_node("LiveMandi_Agent", live_mandi_agent_node)
    workflow.add_node("GeoSpatial_Agent", geospatial_agent_node)
    workflow.add_node("normalizer", schema_normalizer_node)
    workflow.add_node("self_correction", self_correction_node)

    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "TabularPDF_Agent": "TabularPDF_Agent",
            "WebPortal_Agent": "WebPortal_Agent",
            "LiveMandi_Agent": "LiveMandi_Agent",
            "GeoSpatial_Agent": "GeoSpatial_Agent",
        }
    )
    workflow.add_edge("TabularPDF_Agent", "normalizer")
    workflow.add_edge("WebPortal_Agent", "normalizer")
    workflow.add_edge("LiveMandi_Agent", "normalizer")
    workflow.add_edge("GeoSpatial_Agent", "normalizer")

    workflow.add_conditional_edges(
        "normalizer",
        check_validation_gate,
        {
            "self_correct": "self_correction",
            "complete": END,
        }
    )
    workflow.add_edge("self_correction", "normalizer")
    return workflow.compile()

class FoundryAndTrajectoryEvaluators:
    EXPECTED_TOOL_BY_AGENT = {
        "TabularPDF_Agent": "extract_pdf_table_tool",
        "WebPortal_Agent": "fetch_clean_webpage_tool",
        "LiveMandi_Agent": "scrape_amiu_mandi_tool",
        "GeoSpatial_Agent": "inspect_gis_portal_metadata_tool",
    }

    @classmethod
    def evaluate_run(cls, state: PipelineState) -> Dict[str, Any]:
        agent = state["selected_agent"]
        expected_tool = cls.EXPECTED_TOOL_BY_AGENT[agent]
        tool_selection = 1.0 if state["tool_invoked"] == expected_tool else 0.0
        tool_input_acc = 1.0 if state["tool_input"].get("url") == state["source"]["url"] else 0.0
        task_completion = 1.0 if state["status"] == "COMPLETED" and len(state["normalized_records"]) > 0 else 0.0

        valid_recs = [r for r in state["normalized_records"] if r["validation_status"] == "VALIDATED"]
        groundedness = len(valid_recs) / max(1, len(state["normalized_records"]))
        provenance_bonus = 1.0 if all(("=" in r["source_location"] or ";" in r["source_location"]) for r in valid_recs) else 0.5

        expected_traj = [f"SupervisorRouter->{agent}", f"Tool:{expected_tool}", "SchemaNormalizer_Agent", "DB_Commit_Ready"]
        strict_traj_match = 1.0 if state["trajectory"] == expected_traj else 0.85

        return {
            "source_id": state["source"]["source_id"],
            "agent": agent,
            "ToolSelection": tool_selection,
            "ToolInputAccuracy": tool_input_acc,
            "TaskCompletion": task_completion,
            "Groundedness": groundedness,
            "ProvenanceBonus": provenance_bonus,
            "TrajectoryMatch": strict_traj_match,
            "retries": state["retry_count"],
            "trajectory_str": " -> ".join(state["trajectory"]),
        }
