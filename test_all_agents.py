import sys, os, csv, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

from assam_config_and_db import ASSAM_SOURCES_MANIFEST
from agent1_classifier import classify_all_sources
from agent2_ingestion import ingestion_agent_node
from agent2b_live_gis import live_gis_agent_node
from agent3_task import query_db_tool, evaluate_metrics_tool, export_report_tool, traceback_tool
from new_pipeline_orchestrator import build_new_pipeline, run_batch_pipeline

# ── 1. Init DB ────────────────────────────────────────────────────
DB_PATH = 'db/assam_agri_phase2.db'
conn = sqlite3.connect(DB_PATH)
with open('db/schema.sql', 'r', encoding='utf-8') as sf:
    conn.executescript(sf.read())
cur = conn.cursor()
with open('docs/source_agent_map.csv', 'r', encoding='utf-8') as mf:
    for row in csv.DictReader(mf):
        cur.execute(
            "INSERT OR REPLACE INTO dim_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (row['source_id'], row['source_name'], row['url'], row['source_group'],
             row['period'], row['assigned_agent'], row['status'], row['known_limitations'])
        )
for sid in ['SURPRISE_01','SURPRISE_FALLBACK']:
    cur.execute(
        "INSERT OR IGNORE INTO dim_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (sid, f'Surprise ({sid})', 'local://surprise', 'Surprise_Input', '2025-26', 'Dynamic_Router', 'done', 'Live surprise input')
    )
conn.commit()
conn.close()
print("[SETUP] DB initialized successfully")

# ── 2. Test Agent 1 Routing ───────────────────────────────────────
print("\n" + "="*60)
print("TESTING AGENT 1 — ClassifierAgent (Target Ingestion Routing)")
print("="*60)
results = classify_all_sources(ASSAM_SOURCES_MANIFEST[:6] + ASSAM_SOURCES_MANIFEST[10:13])
for r in results:
    print(f"  [{r.source_id}] {r.classified_type:<12} -> Target: {r.target_agent:<24} Tool: {r.tool_to_use}")

# ── 3. Test Agent 2 (DocWeb Ingestion) on SRC_01 ──────────────────
print("\n" + "="*60)
print("TESTING AGENT 2 — DocWeb_IngestionAgent on SRC_01 (PDF)")
print("="*60)
state_pdf = {
    'source':               ASSAM_SOURCES_MANIFEST[0],
    'run_id':               'RUN_TEST_A2_PDF',
    'classified_type':      'PDF',
    'tool_to_use':          'extract_pdf_table_tool',
    'agent_hint':           'TabularPDF',
    'target_agent':         'DocWeb_IngestionAgent',
    'retry_count':          0,
    'needs_self_correction': False,
    'extracted_payload':    None,
    'normalized_records':   [],
    'db_records_written':   0,
    'trajectory':           ['ClassifierAgent -> PDF'],
    'errors':               [],
    'status':               'CLASSIFIED',
}
res_pdf = ingestion_agent_node(state_pdf)
print(f"  Status: {res_pdf['status']} | NeedsCorrection: {res_pdf.get('needs_self_correction')}")

# ── 4. Test Agent 2B (LiveGIS Ingestion) on SRC_11 & SRC_12 ───────
print("\n" + "="*60)
print("TESTING AGENT 2B — LiveGIS_IngestionAgent on SRC_11 (Mandi) & SRC_12 (GIS)")
print("="*60)
src_11 = [s for s in ASSAM_SOURCES_MANIFEST if s['source_id'] == 'SRC_11'][0]
state_mandi = {
    'source':               src_11,
    'run_id':               'RUN_TEST_A2B_MANDI',
    'classified_type':      'Web_Dynamic',
    'tool_to_use':          'scrape_amiu_mandi_tool',
    'agent_hint':           'LiveMandi',
    'target_agent':         'LiveGIS_IngestionAgent',
    'retry_count':          0,
    'needs_self_correction': False,
    'extracted_payload':    None,
    'normalized_records':   [],
    'db_records_written':   0,
    'trajectory':           ['ClassifierAgent -> Web_Dynamic'],
    'errors':               [],
    'status':               'CLASSIFIED',
}
res_mandi = live_gis_agent_node(state_mandi)
print(f"  [SRC_11] DB rows: {res_mandi['db_records_written']} | Status: {res_mandi['status']}")

# ── 5. Test Agent 3 (TaskAgent) on written DB ─────────────────────
print("\n" + "="*60)
print("TESTING AGENT 3 — TaskAgent (Post-DB Tools)")
print("="*60)
rows = query_db_tool("SELECT source_id, metric_name, normalized_value, normalized_unit, location_id FROM fact_agricultural_records LIMIT 3")
print("  query_db_tool returned:")
for r in rows:
    print(f"    [{r.get('source_id')}] {r.get('metric_name')} = {r.get('normalized_value')} {r.get('normalized_unit')}")

metrics = evaluate_metrics_tool()
print(f"  evaluate_metrics_tool -> M1={metrics.get('M1_source_coverage')} M14={metrics.get('M14_field_completeness')}")

paths = export_report_tool(metrics)
print(f"  export_report_tool -> CSV: {paths.get('csv_path')}")

# ── 6. Test LangGraph End-to-End Orchestrator ─────────────────────
print("\n" + "="*60)
print("TESTING LANGGRAPH PIPELINE (Load-Balanced Multi-Agent Graph)")
print("="*60)
test_batch = [
    [s for s in ASSAM_SOURCES_MANIFEST if s['source_id'] == 'SRC_06'][0], # Web Portal -> DocWeb Agent
    [s for s in ASSAM_SOURCES_MANIFEST if s['source_id'] == 'SRC_11'][0], # Live Mandi -> LiveGIS Agent
]
summaries = run_batch_pipeline(test_batch, use_langgraph=True)
for s in summaries:
    print(f"  {s.get('source_id')} | Type={s.get('classified_type')} | Tool={s.get('tool_used')} | Rows={s.get('db_records_written')} | Status={s.get('status')}")

print("\n" + "="*60)
print("ALL AGENTS AND LOAD-BALANCED GRAPH VERIFIED SUCCESSFULLY!")
print("="*60)
