"""
Unit & Integration Test Suite for Independent Multi-Agent Pipeline (test_all_agents.py)
Run: python test_all_agents.py
"""

from agent1_classifier import Agent1Classifier
from agent2_ingestion import Agent2Ingestion
from agent2b_live_gis import Agent2BLiveGIS
from agent3_task import Agent3TaskNormalizer

def test_independent_agents():
    print("=" * 80)
    print("TESTING INDEPENDENT MULTI-AGENT MODULES (Agent 1 -> Agent 2/2B -> Agent 3)")
    print("=" * 80)

    a1 = Agent1Classifier()
    a2 = Agent2Ingestion()
    a2b = Agent2BLiveGIS()
    a3 = Agent3TaskNormalizer()

    # 1. Test Agent 1 Classifier
    c_pdf = a1.classify_source({"filepath": "surprise_samples/surprise_1_district_stats.csv"})
    c_html = a1.classify_source({"filepath": "surprise_samples/surprise_2_aau_bulletin.html"})
    c_gis = a1.classify_source({"source_group": "Geospatial_GIS", "expected_agent": "GeoSpatial_Agent"})
    print(f"[PASS] Agent 1 Classifier : CSV->{c_pdf['specialist_role']} | HTML->{c_html['specialist_role']} | GIS->{c_gis['worker_module']}")

    # 2. Test Agent 2 Ingestion on CSV, HTML, and Assamese TXT
    r_csv = a2.ingest_file("surprise_samples/surprise_1_district_stats.csv")
    r_html = a2.ingest_file("surprise_samples/surprise_2_aau_bulletin.html")
    r_as = a2.ingest_file("surprise_samples/surprise_3_assamese_advisory.txt")
    print(f"[PASS] Agent 2 Ingestion  : Extracted {len(r_csv)} CSV, {len(r_html)} HTML, {len(r_as)} Assamese records")

    # 3. Test Agent 2B Live Mandi & GIS
    r_mandi = a2b.ingest_case_dict({"source_id": "SRC_11", "expected_agent": "LiveMandi_Agent", "structured_source_row": {"crop_name": "Rice (Paddy)", "raw_value": "2250", "raw_unit": "Rs/Quintal"}})
    print(f"[PASS] Agent 2B Live/GIS  : Extracted {len(r_mandi)} Live Mandi record ({r_mandi[0]['raw_value']} {r_mandi[0]['raw_unit']})")

    # 4. Test Agent 3 Normalizer & Self-Correction
    norm_rec = a3.normalize_record(r_csv[0])
    print(f"[PASS] Agent 3 Normalizer : '{r_csv[0]['district_raw']}' -> {norm_rec['location_id']} | '{r_csv[0]['raw_value']} {r_csv[0]['raw_unit']}' -> {norm_rec['normalized_value']} {norm_rec['normalized_unit']} (Retries={norm_rec['retries']})")

if __name__ == "__main__":
    test_independent_agents()
