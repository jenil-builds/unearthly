"""Phase 5 FSM, Grounding, Hallucination & Adapter Hardening Tests."""
import os, tempfile, unittest
from agent3_task import Agent3TaskNormalizer
from ingestion.adapters.csv_adapter import CSVFeedAdapter
from ingestion.adapters.wms_gis_adapter import WMSGISAdapter
from ingestion.grounding import GroundingError, VerbatimGroundingGate
from ingestion.models import AIResponse, RawFetchResult, SourceConfig, SourceRecord
from ingestion.pipeline import SourceOfTruthPipeline
from ingestion.storage import IngestionStorage, utc_now_iso
from ingestion.validator import ZeroFabricationValidator

class _CountingAI:
    def __init__(self, response: AIResponse):
        self.response, self.calls = response, 0
    def call_json(self, agent_name, system_prompt, user_prompt):
        self.calls += 1
        return self.response

def _rec(**overrides) -> SourceRecord:
    base = dict(source_id="SRC_02", source_url="local://test.txt", source_type="Document_PDF", extracting_agent="agent2_ingestion", locator="Page=1;Span=1", crop_name="Rice (Paddy)", variety_name="DRR Dhan", district_raw="Jorhat", time_period="2024", metric_name="Yield", raw_value="5.4", raw_unit="t/ha", verbatim_quote="Jorhat Rice Yield: 5.4 t/ha in 2024", fetched_at_utc=utc_now_iso(), llm_model_id="openai/gpt-oss-120b")
    base.update(overrides)
    return SourceRecord(**base)

class TestPhase5FSMHardening(unittest.TestCase):
    def test_t_per_ha_deterministic_unit_conversion(self):
        self.assertEqual(Agent3TaskNormalizer.normalize_unit(5.4, "t/ha"), (5400.0, "kg/ha"))
        self.assertEqual(Agent3TaskNormalizer.normalize_unit(4.2, "MT/ha"), (4200.0, "kg/ha"))

    def test_grounding_regex_boundaries_and_no_json_brace_bypass(self):
        self.assertFalse(VerbatimGroundingGate.value_in_quote("14", "Released in 2014 in Assam"))
        self.assertFalse(VerbatimGroundingGate.value_in_quote("5", "Yield is 54.5 q/ha"))
        self.assertTrue(VerbatimGroundingGate.value_in_quote("54.5", "Yield is 54.5 q/ha"))
        with self.assertRaises(GroundingError):
            VerbatimGroundingGate.verify_record(_rec(raw_value="999", verbatim_quote='{"yield": "999 t/ha"}', is_structured_table=False), source_text="Actual text says 5.4 t/ha")
        VerbatimGroundingGate.verify_record(_rec(raw_value="5.4", verbatim_quote='{"yield": "5.4"}', is_structured_table=True), source_text="raw csv text")

    def test_validator_blocks_percentage_to_scale_coercion_and_caps_critic_calls(self):
        ai_coerce = _CountingAI(AIResponse({"action": "REPAIR", "raw_value": "14", "raw_unit": "scale", "reason": "coerced"}, "{}", "groq", "openai/gpt-oss-120b", 80, 120.0, False))
        val = ZeroFabricationValidator(ai_runtime=ai_coerce, max_critic_calls_per_batch=2)
        with self.assertRaises(ValueError):
            val.validate_record(_rec(raw_value="14%", raw_unit="%", verbatim_quote="Yield advantage of 14% over check"))
        self.assertEqual(ai_coerce.calls, 0)
        with self.assertRaises(ValueError):
            val.validate_record(_rec(raw_value="44", raw_unit="bushels", verbatim_quote="Output is 44 bushels"))
        self.assertEqual(ai_coerce.calls, 1)

        ai_cap = _CountingAI(AIResponse({"action": "REJECT", "raw_value": None, "raw_unit": None, "reason": "no"}, "{}", "groq", "m", 10, 10.0, False))
        val_cap = ZeroFabricationValidator(ai_runtime=ai_cap, max_critic_calls_per_batch=2)
        valid, rejected, _, _ = val_cap.validate_batch([_rec(raw_value="44", raw_unit="bushels", verbatim_quote="Output is 44 bushels") for _ in range(10)])
        self.assertEqual((len(valid), len(rejected), ai_cap.calls), (0, 10, 2))

    def test_wms_adapter_binds_snapshot_date_for_live_mandi_dashboard(self):
        html = b"<html><body><table><tr><th>Commodity</th><th>Market</th><th>Avg Min Price (Rs.)</th></tr><tr><td>Rice</td><td>Jorhat</td><td>2450</td></tr></table></body></html>"
        cfg = SourceConfig("SRC_11", "AMIU Live", "local://mandi.html", "Database_Dashboard", "wms_gis", "agent2b_live_gis")
        raw = RawFetchResult("SRC_11", cfg.url, "2026-11-24T01:05:00+00:00", 200, False, html, "text/html", content_sha256="s1")
        recs = WMSGISAdapter(ai_runtime=_CountingAI(AIResponse(None, "", "none", "deterministic_fallback", 0, 0.0, True))).parse(cfg, raw)
        self.assertEqual((len(recs), recs[0].time_period, recs[0].is_structured_table), (1, "2026-11-24", True))

    def test_empty_parse_is_degraded_and_not_cached(self):
        with tempfile.TemporaryDirectory() as td:
            db_path, empty_html = os.path.join(td, "fsm.db"), os.path.join(td, "empty.html")
            with open(empty_html, "w", encoding="utf-8") as f:
                f.write("<html><body><p>No agricultural statistics here.</p></body></html>")
            storage = IngestionStorage(db_path=db_path, schema_path="db/schema.sql")
            pipe = SourceOfTruthPipeline(storage=storage, enable_ai_triage=False)
            cfg = SourceConfig("SRC_06", "Empty Page", empty_html, "Web_Portal", "html_table", "agent2_ingestion")
            self.assertEqual(pipe.run_source(cfg).fetch_status, "EMPTY_PARSE")
            h1 = storage.get_source_health("SRC_06")
            self.assertEqual((h1["health_status"], h1["last_content_sha256"]), ("DEGRADED", None))
            self.assertEqual(pipe.run_source(cfg).fetch_status, "EMPTY_PARSE")

    def test_csv_utf8_bom_and_pipeline_no_bom(self):
        with open("ingestion/pipeline.py", "rb") as f:
            self.assertNotEqual(f.read(3), b"\xef\xbb\xbf")
        bom_csv = "\ufeffcrop_name,district_raw,time_period,metric_name,raw_value,raw_unit\nRice,Jorhat,2025,Area,1000,ha\n".encode("utf-8")
        cfg = SourceConfig("SRC_01", "BOM CSV", "local://bom.csv", "Document_PDF", "csv_feed", "agent2_ingestion")
        raw = RawFetchResult("SRC_01", cfg.url, utc_now_iso(), 200, False, bom_csv, "text/csv", content_sha256="b1")
        recs = CSVFeedAdapter(ai_runtime=_CountingAI(AIResponse(None, "", "none", "deterministic_fallback", 0, 0.0, True))).parse(cfg, raw)
        self.assertEqual((len(recs), recs[0].crop_name), (1, "Rice"))

if __name__ == "__main__":
    unittest.main()
