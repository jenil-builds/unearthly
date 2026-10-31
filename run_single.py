"""
Run pipeline for a specific source ID from docs/source_agent_map.csv (e.g., SRC_01..SRC_15).
Usage: python run_single.py --source SRC_01
"""
import os
import json
import sqlite3
import argparse
from new_pipeline_orchestrator import MultiAgentOrchestrator

def main():
    parser = argparse.ArgumentParser(description="Run MultiAgentOrchestrator for a single source_id")
    parser.add_argument("--source", type=str, required=True, help="Source ID (e.g., SRC_01, SRC_07, SRC_11)")
    args = parser.parse_args()

    orch = MultiAgentOrchestrator(db_path="db/assam_agri_phase2.db")
    matched_cases = []
    for fn in sorted(os.listdir("eval/cases")):
        if fn.endswith(".json"):
            fp = os.path.join("eval/cases", fn)
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("source_id") == args.source:
                matched_cases.extend(orch._process_single_case(fp))

    if not matched_cases:
        print(f"[ERROR] No evaluation cases found for source_id='{args.source}'.")
        return

    orch.run_pipeline()
    conn = sqlite3.connect("db/assam_agri_phase2.db")
    rows = conn.execute("""
        SELECT record_id, source_id, extracting_agent, source_location, location_id,
               metric_name, raw_value_text, raw_unit, normalized_value, normalized_unit
        FROM fact_agricultural_records
        WHERE source_id = ?
    """, (args.source,)).fetchall()
    conn.close()

    print(f"\n[SUCCESS] Verified {len(rows)} committed records in db/assam_agri_phase2.db for {args.source}:")
    for r in rows:
        print(f"  Row #{r[0]:02d} | Agent={r[2]} | Loc='{r[3]}' | LGD={r[4]} | {r[5]}: '{r[6]} {r[7]}' -> {r[8]:,.2f} {r[9]}")

if __name__ == "__main__":
    main()
