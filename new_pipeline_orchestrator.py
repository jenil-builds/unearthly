"""
NEW PIPELINE ORCHESTRATOR: new_pipeline_orchestrator.py
=============================================================
LangGraph StateGraph connecting all 3 agents in sequence:

    ClassifierAgent (Agent 1)
          ↓
    IngestionAgent (Agent 2) ←─────────────┐
          ↓                                │
    SelfCorrectionNode (if * found)  ──────┘
          ↓
    TaskAgent (Agent 3)
          ↓
         END

Pipeline State flows through all 3 agents, accumulating results.
Each agent reads what it needs and writes its outputs back to state.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, TypedDict

# ── Import agent nodes ──────────────────────────────────────────
from agent1_classifier import classifier_agent_node
from agent2_ingestion  import ingestion_agent_node, ingestion_self_correction_node
from agent2b_live_gis  import live_gis_agent_node
from agent3_task       import task_agent_node

# ── LangGraph (optional — falls back to manual runner if not installed) ───
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────
# PIPELINE STATE DEFINITION
# Shared dictionary passed through all agents
# ─────────────────────────────────────────────────────────────────

class NewPipelineState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────
    source:   Dict[str, Any]   # Raw source manifest entry
    run_id:   str              # Unique run identifier

    # ── Agent 1 outputs (ClassifierAgent) ─────────────────────────
    classified_type:           str    # PDF | Web | Web_Dynamic | Web_GIS
    tool_to_use:               str    # Which extraction tool to use
    agent_hint:                str    # TabularPDF | WebPortal | LiveMandi | GeoSpatial
    target_agent:              str    # DocWeb_IngestionAgent | LiveGIS_IngestionAgent
    classification_confidence: float  # 0.0–1.0

    # ── Agent 2 outputs (IngestionAgent) ──────────────────────────
    tool_invoked:         str                   # Name of tool that was called
    tool_input:           Dict[str, Any]        # Arguments passed to tool
    raw_tool_output:      str                   # Raw tool response
    extracted_payload:    Optional[Dict[str, Any]]  # LLM structured output
    normalized_records:   List[Dict[str, Any]]  # DB-ready rows
    db_records_written:   int                   # Count written to DB
    retry_count:          int                   # How many self-corrections ran
    needs_self_correction: bool                 # Flag for SelfCorrectionNode

    # ── Agent 3 outputs (TaskAgent) ───────────────────────────────
    query_results: List[Dict[str, Any]]   # SQL query results from DB
    eval_metrics:  Dict[str, Any]         # M1–M18 computed metrics
    report_paths:  Dict[str, str]         # {"csv_path": ..., "md_path": ...}
    task_results:  Dict[str, Any]         # Combined task output summary

    # ── Pipeline-wide ─────────────────────────────────────────────
    trajectory: List[str]   # Full step-by-step trace of all decisions
    errors:     List[str]   # Any non-fatal errors encountered
    status:     str         # INIT | CLASSIFIED | INGESTED | COMPLETED | FAILED


def _make_initial_state(source: Dict[str, Any]) -> NewPipelineState:
    """Creates a fresh initial state dict for a single source."""
    return {
        "source":   source,
        "run_id":   f"RUN3A_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6].upper()}",

        # Agent 1 (filled by ClassifierAgent)
        "classified_type":           "",
        "tool_to_use":               "",
        "agent_hint":                "",
        "target_agent":              "",
        "classification_confidence": 0.0,

        # Ingestion outputs (DocWeb or LiveGIS)
        "tool_invoked":           "",
        "tool_input":             {},
        "raw_tool_output":        "",
        "extracted_payload":      None,
        "normalized_records":     [],
        "db_records_written":     0,
        "retry_count":            0,
        "needs_self_correction":  False,

        # Agent 3 (filled by TaskAgent)
        "query_results": [],
        "eval_metrics":  {},
        "report_paths":  {},
        "task_results":  {},

        # Pipeline-wide
        "trajectory": [f"Pipeline START: {source.get('source_id','?')}"],
        "errors":     [],
        "status":     "INIT",
    }


# ─────────────────────────────────────────────────────────────────
# CONDITIONAL ROUTING
# ─────────────────────────────────────────────────────────────────

def _route_after_classifier(state: NewPipelineState) -> str:
    """
    After ClassifierAgent runs:
    - If Live Mandi or GeoSpatial GIS -> route to LiveGIS_IngestionAgent
    - Otherwise (PDF or Web portals)   -> route to DocWeb IngestionAgent
    """
    if (
        state.get("target_agent") == "LiveGIS_IngestionAgent"
        or state.get("classified_type") in ("Web_Dynamic", "Web_GIS")
    ):
        return "live_gis"
    return "doc_ingest"


def _route_after_ingestion(state: NewPipelineState) -> str:
    """
    After DocWeb Ingestion runs:
    - If footnote found AND retries < 2 → go to SelfCorrectionNode
    - Else → go to TaskAgent
    """
    if state.get("needs_self_correction") and state.get("retry_count", 0) < 2:
        return "self_correct"
    return "task"


def _route_after_self_correction(state: NewPipelineState) -> str:
    """After SelfCorrectionNode: always go back to IngestionAgent to re-normalize."""
    return "doc_ingest"


# ─────────────────────────────────────────────────────────────────
# BUILD LANGGRAPH COMPILED PIPELINE
# ─────────────────────────────────────────────────────────────────

def build_new_pipeline():
    """
    Builds and compiles the load-balanced multi-agent LangGraph StateGraph.

    Graph structure:
        START
          → classifier (Agent 1)
                ├─(Web_Dynamic / Web_GIS)─→ live_gis_ingestion (LiveGIS Agent) ──────┐
                └─(PDF / Web Portals)────→ doc_ingestion      (DocWeb Agent)         │
                                                 ↓                                   │
                                            [self_correction]                        │
                                                 ↓                                   │
                                            doc_ingestion                            │
                                                 ↓                                   │
                                              task (TaskAgent)  <────────────────────┘
                                                 ↓
                                                END
    """
    if not LANGGRAPH_AVAILABLE:
        print("[Orchestrator] LangGraph not installed — using sequential fallback runner.")
        return None

    workflow = StateGraph(NewPipelineState)

    # ── Register nodes ────────────────────────────────────────────
    workflow.add_node("classifier",          classifier_agent_node)
    workflow.add_node("doc_ingestion",       ingestion_agent_node)
    workflow.add_node("live_gis_ingestion",  live_gis_agent_node)
    workflow.add_node("self_correction",     ingestion_self_correction_node)
    workflow.add_node("task",                task_agent_node)

    # ── Define edges ──────────────────────────────────────────────
    workflow.set_entry_point("classifier")

    # Classifier branches to either DocWeb Ingestion or LiveGIS Ingestion
    workflow.add_conditional_edges(
        "classifier",
        _route_after_classifier,
        {
            "doc_ingest": "doc_ingestion",
            "live_gis":   "live_gis_ingestion",
        }
    )

    # DocWeb Ingestion branches to self_correction or task
    workflow.add_conditional_edges(
        "doc_ingestion",
        _route_after_ingestion,
        {
            "self_correct": "self_correction",
            "task":         "task",
        }
    )

    # Self-correction loops back to DocWeb ingestion
    workflow.add_conditional_edges(
        "self_correction",
        _route_after_self_correction,
        {
            "doc_ingest": "doc_ingestion",
        }
    )

    # LiveGIS Ingestion converges directly to TaskAgent
    workflow.add_edge("live_gis_ingestion", "task")
    workflow.add_edge("task", END)

    compiled = workflow.compile()
    print("[Orchestrator] OK Multi-Agent Load-Balanced LangGraph pipeline compiled successfully.")
    return compiled


# ─────────────────────────────────────────────────────────────────
# SEQUENTIAL FALLBACK RUNNER
# ─────────────────────────────────────────────────────────────────

def run_pipeline_sequential(source: Dict[str, Any]) -> NewPipelineState:
    """Runs the multi-agent pipeline manually without LangGraph."""
    state = _make_initial_state(source)

    # Agent 1: Classify
    state = classifier_agent_node(state)
    state["status"] = "CLASSIFIED"

    # Branch between DocWeb Ingestion vs LiveGIS Ingestion
    if (
        state.get("target_agent") == "LiveGIS_IngestionAgent"
        or state.get("classified_type") in ("Web_Dynamic", "Web_GIS")
    ):
        state = live_gis_agent_node(state)
        state["status"] = "INGESTED"
    else:
        max_retries = 2
        for attempt in range(max_retries + 1):
            state = ingestion_agent_node(state)

            if state.get("needs_self_correction") and state.get("retry_count", 0) < max_retries:
                state = ingestion_self_correction_node(state)
            else:
                state["status"] = "INGESTED"
                break

    # Agent 3: Task
    state = task_agent_node(state)
    state["status"] = "COMPLETED"

    return state


# ─────────────────────────────────────────────────────────────────
# BATCH PIPELINE RUNNER
# Processes multiple sources through the 3-agent pipeline
# ─────────────────────────────────────────────────────────────────

def run_batch_pipeline(
    sources: List[Dict[str, Any]],
    use_langgraph: bool = True
) -> List[Dict[str, Any]]:
    """
    Runs the 3-agent pipeline for a list of sources (batch mode).

    For each source:
      1. Creates a fresh pipeline state
      2. Runs: ClassifierAgent → IngestionAgent → TaskAgent
      3. Collects and returns final state summaries

    Args:
        sources       : List of source manifest dicts
        use_langgraph : If True and LangGraph available, use compiled graph.
                        If False, uses sequential fallback runner.

    Returns:
        List of summary dicts, one per source
    """
    compiled_pipeline = None
    if use_langgraph and LANGGRAPH_AVAILABLE:
        compiled_pipeline = build_new_pipeline()

    summaries = []

    for i, src in enumerate(sources, 1):
        print(f"\n{'='*70}")
        print(f"[Batch] Processing {i}/{len(sources)}: {src.get('source_id','?')} — {src.get('name', src.get('source_name',''))[:60]}")
        print(f"{'='*70}")

        try:
            if compiled_pipeline:
                initial_state = _make_initial_state(src)
                final_state   = compiled_pipeline.invoke(initial_state)
            else:
                final_state = run_pipeline_sequential(src)

            summaries.append({
                "source_id":            src.get("source_id"),
                "status":               final_state.get("status", "UNKNOWN"),
                "classified_type":      final_state.get("classified_type", "?"),
                "tool_used":            final_state.get("tool_invoked", "?"),
                "db_records_written":   final_state.get("db_records_written", 0),
                "retry_count":          final_state.get("retry_count", 0),
                "trajectory_steps":     len(final_state.get("trajectory", [])),
                "errors":               final_state.get("errors", []),
                "m14_completeness":     final_state.get("eval_metrics", {}).get("M14_field_completeness", "?"),
                "m15_validation":       final_state.get("eval_metrics", {}).get("M15_validation_pass_rate", "?"),
                "m16_duplicates":       final_state.get("eval_metrics", {}).get("M16_duplicate_rate", "?"),
            })

        except Exception as e:
            print(f"  [Batch][ERROR] {src.get('source_id','?')} failed: {e}")
            summaries.append({
                "source_id": src.get("source_id"),
                "status":    "FAILED",
                "error":     str(e),
            })

    return summaries


# ─────────────────────────────────────────────────────────────────
# PRINT FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────

def print_pipeline_summary(summaries: List[Dict[str, Any]]):
    """Prints a formatted table of batch pipeline results."""
    print("\n" + "=" * 100)
    print("3-AGENT PIPELINE — BATCH RUN SUMMARY")
    print("=" * 100)
    print(f"{'SrcID':<10} {'Status':<12} {'Type':<15} {'Tool':<35} {'DB_Rows':>7} {'Retries':>7} {'M14':>5} {'M15':>5} {'M16':>5}")
    print("-" * 100)
    for s in summaries:
        print(
            f"{s.get('source_id','?'):<10} "
            f"{s.get('status','?'):<12} "
            f"{s.get('classified_type','?'):<15} "
            f"{s.get('tool_used','?'):<35} "
            f"{s.get('db_records_written',0):>7} "
            f"{s.get('retry_count',0):>7} "
            f"{str(s.get('m14_completeness','?')):>5} "
            f"{str(s.get('m15_validation','?')):>5} "
            f"{str(s.get('m16_duplicates','?')):>5}"
        )
    done  = sum(1 for s in summaries if s.get("status") == "COMPLETED")
    fails = sum(1 for s in summaries if s.get("status") == "FAILED")
    total_db = sum(s.get("db_records_written", 0) for s in summaries)
    print("-" * 100)
    print(f"✅ Completed: {done}/{len(summaries)} | ❌ Failed: {fails} | Total DB records written: {total_db}")
    print("=" * 100)
