"""
Unit & Integration Test Suite for Independent Multi-Agent Pipeline (test_all_agents.py)
"""
from agent1_classifier import Agent1Classifier
from agent2_ingestion import Agent2Ingestion
from agent2b_live_gis import Agent2BLiveGIS
from agent3_task import Agent3TaskNormalizer

def test_independent_agents():
    print("=" * 80)
    print("TESTING INDEPENDENT MULTI-AGENT MODULES (agent1_classifier -> agent2/2b -> agent3_task)")
    print("=" * 80)

    a1 = Agent1Classifier()
    a2 = Agent2Ingestion()
    a2b = Agent2BLiveGIS()
    a3 = Agent3TaskNormalizer()

    c_csv = a1.classify_source({"filepath": "surprise_samples/surprise_1_district_stats.csv"})
    c_html = a1.classify_source({"filepath": "surprise_samples/surprise_2_aau_bulletin.html"})
    c_gis = a1.classify_source({"source_group": "Geospatial_GIS"})
    assert c_csv["target_agent"] == "agent2_ingestion"
    assert c_html["target_agent"] == "agent2_ingestion"
    assert c_gis["target_agent"] == "agent2b_live_gis"
    print(f"[PASS] agent1_classifier : CSV->{c_csv['target_agent']} | HTML->{c_html['target_agent']} | GIS->{c_gis['target_agent']}")

    r_csv = a2.ingest_file("surprise_samples/surprise_1_district_stats.csv")
    r_html = a2.ingest_file("surprise_samples/surprise_2_aau_bulletin.html")
    r_as = a2.ingest_file("surprise_samples/surprise_3_assamese_advisory.txt")
    print(f"[PASS] agent2_ingestion  : Extracted {len(r_csv)} CSV, {len(r_html)} HTML, {len(r_as)} Assamese records")

    r_mandi = a2b.ingest_case_dict({"source_id": "SRC_11", "source_group": "Database_Dashboard", "structured_source_row": {"crop_name": "Rice (Paddy)", "raw_value": "2250", "raw_unit": "Rs/Quintal"}})
    assert r_mandi[0]["agent"] == "agent2b_live_gis"
    print(f"[PASS] agent2b_live_gis  : Extracted {len(r_mandi)} Live Mandi record ({r_mandi[0]['raw_value']} {r_mandi[0]['raw_unit']})")

    norm_rec = a3.normalize_record(r_csv[0])
    assert norm_rec["agent"] == "agent2_ingestion"
    assert norm_rec["validation_status"] == "SELF_CORRECTED"
    print(f"[PASS] agent3_task       : '{r_csv[0]['district_raw']}' -> {norm_rec['location_id']} | '{r_csv[0]['raw_value']} {r_csv[0]['raw_unit']}' -> {norm_rec['normalized_value']} {norm_rec['normalized_unit']} (Status={norm_rec['validation_status']}, Retries={norm_rec['retries']})")

if __name__ == "__main__":
    test_independent_agents()
