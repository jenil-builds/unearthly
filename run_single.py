"""
save as: run_single.py
run:     python run_single.py --source SRC_01
"""
import argparse
import sqlite3
from assam_config_and_db import ASSAM_SOURCES_MANIFEST
from phase2_assam_complete_demo import execute_single_source, persist_state_to_db, build_compiled_langgraph

def run_single_source(target_source_id: str):
    # 1. Find the specific source in the manifest
    src = next((s for s in ASSAM_SOURCES_MANIFEST if s["source_id"] == target_source_id), None)
    
    if not src:
        print(f"[ERROR] Source '{target_source_id}' not found in manifest.")
        print("Available IDs: " + ", ".join(s["source_id"] for s in ASSAM_SOURCES_MANIFEST))
        return

    print("=" * 80)
    print(f"RUNNING LIVE PIPELINE FOR: {src['source_id']} - {src['name']}")
    print(f"URL: {src['url']}")
    print("=" * 80)

    # 2. Connect to the database (using the official Phase 2 'db/' folder path)
    conn = sqlite3.connect("db/assam_agri_phase2.db")
    
    # 3. Build the LangGraph orchestrator
    compiled_graph = build_compiled_langgraph()
    
    # 4. Execute the pipeline for this single source
    print(f"Routing to {src['assigned_agent']}...")
    final_state = execute_single_source(compiled_graph, src, idx=999)
    
    # 5. Persist the extracted and normalized records to the database
    persist_state_to_db(conn, final_state)
    
    # 6. Show the user what was saved
    records = final_state.get("normalized_records", [])
    print(f"\n[SUCCESS] Extracted {len(records)} records and saved them to the database!")
    for r in records:
        print(f" -> Crop: {r['crop_name']} | District: {r['canonical_district']} | Value: {r['normalized_value']} {r['normalized_unit']}")
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, required=True, help="The ID of the source to run (e.g., SRC_01, SRC_06)")
    args = parser.parse_args()
    
    run_single_source(args.source)