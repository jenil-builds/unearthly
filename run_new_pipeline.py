"""
ENTRY POINT: run_new_pipeline.py
=============================================================
CLI entry point for the Multi-Agent Pipeline.

Architecture:
    Agent 1 (ClassifierAgent)
         │
         ├──[PDF / Web Portals]───────► Agent 2  (DocWeb_IngestionAgent)
         │                                    │ (extract_pdf_table_tool, fetch_clean_webpage_tool)
         │                                    ▼
         │                               [SelfCorrectionNode if * found]
         │                                    │
         └──[Live Mandi / Web GIS]────► Agent 2B (LiveGIS_IngestionAgent)
                                              │ (scrape_amiu_mandi_tool, inspect_gis_metadata)
                                              ▼
                                         [SQLite Database]
                                              │
                                              ▼
                                        Agent 3  (TaskAgent)
                                              │ (query_db, evaluate_metrics, export_report, traceback)
                                              ▼
                                             END
"""

import os
import sys
import re
import csv
import json
import argparse
import sqlite3
from datetime import datetime, timezone

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Existing config (unchanged — backward compatible) ─────────────
from assam_config_and_db import ASSAM_SOURCES_MANIFEST

# ── New 3-agent pipeline ──────────────────────────────────────────
from agent1_classifier       import classify_all_sources
from agent3_task             import query_db_tool, evaluate_metrics_tool, export_report_tool, traceback_tool
from new_pipeline_orchestrator import (
    run_batch_pipeline,
    run_pipeline_sequential,
    print_pipeline_summary,
    build_new_pipeline,
    LANGGRAPH_AVAILABLE,
)


# ─────────────────────────────────────────────────────────────────
# SURPRISE FILE PARSER
# Converts unseen files into source-like dicts that Agent 1 can classify
# ─────────────────────────────────────────────────────────────────

def parse_surprise_as_source(filepath: str) -> dict:
    """
    Wraps a surprise input file as a pseudo-source dict so it can
    go through the same 3-agent pipeline as regular manifest sources.
    """
    ext  = os.path.splitext(filepath)[1].lower()
    name = os.path.basename(filepath)

    # Infer modality from extension for Agent 1's classify_source_tool
    modality_map = {
        ".pdf":  "PDF",
        ".html": "Web",
        ".htm":  "Web",
        ".csv":  "PDF",       # tabular → TabularPDF agent handles CSVs too
        ".json": "PDF",       # structured → TabularPDF agent
        ".txt":  "Web",       # text advisory → WebPortal agent
    }
    modality = modality_map.get(ext, "Web")

    return {
        "source_id":   f"SURPRISE_{name.upper().replace('.','_').replace('-','_')}",
        "name":        f"Surprise Input: {name}",
        "url":         f"local://{os.path.abspath(filepath)}",
        "modality":    modality,
        "period":      "2025-26",
        "status":      "surprise_input",
        "limitation":  "Unseen surprise file for live evaluation",
        # Pass the local file path so IngestionAgent can read it
        "_local_path": os.path.abspath(filepath),
    }


def load_surprise_sources(path: str) -> list:
    """Load all surprise files from a path (file or directory)."""
    sources = []
    if os.path.isdir(path):
        for fn in sorted(os.listdir(path)):
            fp = os.path.join(path, fn)
            if os.path.isfile(fp):
                sources.append(parse_surprise_as_source(fp))
    elif os.path.isfile(path):
        sources.append(parse_surprise_as_source(path))
    return sources


# ─────────────────────────────────────────────────────────────────
# CLASSIFY-ONLY MODE (Agent 1 only)
# ─────────────────────────────────────────────────────────────────

def run_classify_only():
    """Run Agent 1 only — show classification of all 15 sources."""
    print("\n" + "=" * 80)
    print("AGENT 1 ONLY — ClassifierAgent: Classifying all 15 sources")
    print("=" * 80)

    results = classify_all_sources(ASSAM_SOURCES_MANIFEST)

    print(f"\n{'SrcID':<9} {'Type':<13} {'Target Agent':<25} {'Tool':<35} {'Conf':>5}")
    print("-" * 92)
    for r in results:
        target = getattr(r, 'target_agent', 'DocWeb_IngestionAgent')
        print(
            f"{r.source_id:<9} {r.classified_type:<13} "
            f"{target:<25} {r.tool_to_use:<35} {r.confidence:>5.0%}"
        )
    print(f"\n✅ Classified {len(results)}/15 sources.")


# ─────────────────────────────────────────────────────────────────
# TASK-ONLY MODE (Agent 3 only — DB must already exist)
# ─────────────────────────────────────────────────────────────────

def run_task_only():
    """Run Agent 3 only — query existing DB and generate report."""
    print("\n" + "=" * 80)
    print("AGENT 3 ONLY — TaskAgent: Querying existing DB + Generating Report")
    print("=" * 80)

    # Tool 1: Query DB
    print("\n── query_db_tool: Top 10 records ────────────────────────")
    rows = query_db_tool(
        "SELECT source_id, metric_name, normalized_value, normalized_unit, location_id "
        "FROM fact_agricultural_records ORDER BY record_id DESC LIMIT 10"
    )
    if rows and "error" not in rows[0]:
        for r in rows:
            print(f"  [{r['source_id']}] {r['metric_name']} = {r['normalized_value']} {r['normalized_unit']} @ {r['location_id']}")
    else:
        print(f"  {rows}")

    # Tool 2: Evaluate metrics
    print("\n── evaluate_metrics_tool: Computing M1–M18 ──────────────")
    metrics = evaluate_metrics_tool()
    for k, v in metrics.items():
        if k != "per_agent_breakdown":
            print(f"  {k}: {v}")

    # Tool 3: Export report
    print("\n── export_report_tool: Writing reports ──────────────────")
    paths = export_report_tool(metrics)
    print(f"  CSV  → {paths['csv_path']}")
    print(f"  MD   → {paths['md_path']}")

    # Tool 4: Traceback
    print("\n── traceback_tool: SRC_01 provenance ────────────────────")
    tb = traceback_tool(source_id="SRC_01")
    for rec in tb.get("traceback_results", [])[:2]:
        print(f"  Source  : {rec.get('source_name','?')}")
        print(f"  Locator : {rec.get('source_location','?')}")
        print(f"  RawValue: {rec.get('raw_value_text','?')} {rec.get('raw_unit','?')}")
        print(f"  Norm    : {rec.get('normalized_value','?')} {rec.get('normalized_unit','?')}")
        print()


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AgriAgent — New 3-Agent Pipeline (Classify → Ingest → Task)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_new_pipeline.py
  python run_new_pipeline.py --source SRC_01
  python run_new_pipeline.py --input surprise_samples/
  python run_new_pipeline.py --classify-only
  python run_new_pipeline.py --task-only
  python run_new_pipeline.py --no-langgraph
        """
    )
    parser.add_argument("--source",        type=str, help="Run only one source, e.g. SRC_01")
    parser.add_argument("--input",         type=str, help="Path to surprise file or directory")
    parser.add_argument("--classify-only", action="store_true", help="Run Agent 1 only (classification)")
    parser.add_argument("--task-only",     action="store_true", help="Run Agent 3 only (query existing DB)")
    parser.add_argument("--no-langgraph",  action="store_true", help="Use sequential fallback instead of LangGraph")
    args = parser.parse_args()

    # ── Special modes ──────────────────────────────────────────────
    if args.classify_only:
        run_classify_only()
        return

    if args.task_only:
        run_task_only()
        return

    # ── Initialize DB (always do this first) ──────────────────────
    print("\n[Setup] Initializing SQLite database...")
    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect("db/assam_agri_phase2.db")
    if os.path.exists("db/schema.sql"):
        with open("db/schema.sql", "r", encoding="utf-8") as sf:
            conn.executescript(sf.read())
        if os.path.exists("docs/source_agent_map.csv"):
            cur = conn.cursor()
            with open("docs/source_agent_map.csv", "r", encoding="utf-8") as mf:
                for row in csv.DictReader(mf):
                    cur.execute(
                        "INSERT OR REPLACE INTO dim_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (row["source_id"], row["source_name"], row["url"], row["source_group"], row["period"], row["assigned_agent"], row["status"], row["known_limitations"])
                    )
            conn.commit()
    conn.close()
    print("[Setup] DB ready: db/assam_agri_phase2.db")

    # ── Select sources to process ─────────────────────────────────
    if args.input:
        sources = load_surprise_sources(args.input)
        print(f"\n[Mode] SURPRISE INPUT: {len(sources)} file(s) from {args.input}")
        for s in sources:
            print(f"  → {s['source_id']} | modality={s['modality']} | {s['url']}")

    elif args.source:
        sources = [s for s in ASSAM_SOURCES_MANIFEST if s["source_id"] == args.source]
        if not sources:
            print(f"[ERROR] Source '{args.source}' not found in manifest.")
            print(f"  Valid IDs: {[s['source_id'] for s in ASSAM_SOURCES_MANIFEST]}")
            return
        print(f"\n[Mode] SINGLE SOURCE: {args.source}")

    else:
        sources = ASSAM_SOURCES_MANIFEST
        print(f"\n[Mode] FULL BATCH: All {len(sources)} sources from manifest")

    # ── Run 3-agent pipeline ───────────────────────────────────────
    use_lg = not args.no_langgraph
    if use_lg and LANGGRAPH_AVAILABLE:
        print(f"\n[Pipeline] Using LangGraph StateGraph")
    else:
        print(f"\n[Pipeline] Using Sequential Fallback Runner")

    summaries = run_batch_pipeline(sources, use_langgraph=use_lg)

    # ── Print summary table ────────────────────────────────────────
    print_pipeline_summary(summaries)

    # ── Final DB stats ─────────────────────────────────────────────
    print("\n[Final] Running Agent 3 full report on completed DB...")
    metrics = evaluate_metrics_tool()
    export_report_tool(metrics)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Total sources processed : {len(summaries)}")
    print(f"  Total DB records        : {metrics.get('total_db_records', '?')}")
    print(f"  M1  Source Coverage     : {metrics.get('M1_source_coverage', '?')}")
    print(f"  M14 Field Completeness  : {metrics.get('M14_field_completeness', '?')}")
    print(f"  M15 Validation Pass     : {metrics.get('M15_validation_pass_rate', '?')}")
    print(f"  M16 Duplicate Rate      : {metrics.get('M16_duplicate_rate', '?')}")
    print(f"  Report CSV              : eval/phase2_metrics_new.csv")
    print(f"  Report MD               : eval/phase2_report_new.md")
    print("=" * 70)


if __name__ == "__main__":
    main()
