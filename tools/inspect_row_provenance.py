"""
Live Provenance Trace-Back Inspector for M4 & M17
Usage:
  python tools/inspect_row_provenance.py
  python tools/inspect_row_provenance.py --rows 1 7 15
"""
import sqlite3
import argparse

def inspect_rows(row_ids=None):
    conn = sqlite3.connect("db/assam_agri_phase2.db")
    cur = conn.cursor()
    if row_ids:
        placeholders = ",".join("?" for _ in row_ids)
        query = f"""
            SELECT f.record_id, f.source_id, s.source_name, s.source_url, f.source_type,
                   f.extracting_agent, f.run_id, f.source_location,
                   l.canonical_district_name, f.location_id, c.crop_name, c.variety_name,
                   f.time_period, f.metric_name, f.raw_value_text, f.raw_unit,
                   f.normalized_value, f.normalized_unit
            FROM fact_agricultural_records f
            JOIN dim_sources s ON f.source_id = s.source_id
            JOIN dim_locations l ON f.location_id = l.location_id
            JOIN dim_crops c ON f.crop_id = c.crop_id
            WHERE f.record_id IN ({placeholders})
        """
        cur.execute(query, row_ids)
    else:
        cur.execute("""
            SELECT f.record_id, f.source_id, s.source_name, s.source_url, f.source_type,
                   f.extracting_agent, f.run_id, f.source_location,
                   l.canonical_district_name, f.location_id, c.crop_name, c.variety_name,
                   f.time_period, f.metric_name, f.raw_value_text, f.raw_unit,
                   f.normalized_value, f.normalized_unit
            FROM fact_agricultural_records f
            JOIN dim_sources s ON f.source_id = s.source_id
            JOIN dim_locations l ON f.location_id = l.location_id
            JOIN dim_crops c ON f.crop_id = c.crop_id
            WHERE f.record_id IN (1, 15, 21)
        """)

    print("=" * 95)
    print("M4 & M17 LIVE EVALUATOR TRACE-BACK VERIFICATION (DB ROW -> EXACT SOURCE LOCATION)")
    print("=" * 95)
    for r in cur.fetchall():
        print(f"DB Record ID     : #{r[0]} (Run ID: {r[6]})")
        print(f"Source & Type    : [{r[1]}] {r[2]} ({r[4]})")
        print(f"Source URL       : {r[3]}")
        print(f"Extracting Agent : {r[5]}")
        print(f"Exact Locator    : {r[7]}")
        print(f"Entity Grounding : Crop='{r[10]} ({r[11]})' | District='{r[8]}' [{r[9]}] | Period='{r[12]}'")
        print(f"Value & SI Unit  : {r[13]} = Raw '{r[14]} {r[15]}' --> Normalized: {r[16]:,.2f} {r[17]}")
        print("-" * 95)
    conn.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rows", nargs="*", type=int, default=None, help="Specific DB record_id numbers picked by evaluator")
    args = p.parse_args()
    inspect_rows(args.rows)
