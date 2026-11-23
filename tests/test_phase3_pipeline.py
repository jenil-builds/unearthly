"""Phase 3 Unit, Integration & Failure Scenario Tests."""
import os, sqlite3, tempfile, unittest
from ingestion.grounding import GroundingError, VerbatimGroundingGate
from ingestion.models import AIResponse, SourceConfig, SourceRecord
from ingestion.pipeline import SourceOfTruthPipeline, load_sources_from_csv
from ingestion.storage import IngestionStorage, utc_now_iso
from ingestion.validator import ZeroFabricationValidator

class _ScriptedAI:
    def __init__(self, responses_by_agent):
        self.responses = responses_by_agent
    def call_json(self, agent_name, system_prompt, user_prompt):
        val = self.responses.get(agent_name)
        if callable(val): return val(user_prompt)
        return val if val is not None else AIResponse(None, "", "none", "deterministic_fallback", 0, 0.0, True)

def _sample_record(**overrides) -> SourceRecord:
    base = dict(source_id="SRC_01", source_url="local://test.txt", source_type="Web_Portal", extracting_agent="agent2_ingestion", locator="TXT=SRC_01;Span=1", crop_name="Rice (Paddy)", variety_name="Ranjit Sub-1", district_raw="Jorhat", time_period="2025-26", metric_name="Potential_Yield", raw_value="54.5", raw_unit="q/ha", verbatim_quote="Jorhat Rice Potential_Yield: 54.5 q/ha in 2025-26", fetched_at_utc=utc_now_iso(), llm_model_id="openai/gpt-oss-120b")
    base.update(overrides)
    return SourceRecord(**base)

class TestPhase3GroundingValidatorPipeline(unittest.TestCase):
    def test_grounding_gate_blocks_fabrication_and_accepts_assamese(self):
        with self.assertRaises(GroundingError): VerbatimGroundingGate.verify_record(_sample_record(time_period=""))
        with self.assertRaises(GroundingError): VerbatimGroundingGate.verify_record(_sample_record(raw_value="999.9"))
        with self.assertRaises(GroundingError): VerbatimGroundingGate.verify_record(_sample_record(), source_text="Unrelated text.")
        VerbatimGroundingGate.verify_record(_sample_record(district_raw="যোৰহাট", raw_value="54.5", raw_unit="q/ha", verbatim_quote="উৎপাদন ক্ষমতা: ৫৪.৫ কুইণ্টল/হেক্টৰ"), source_text="শস্য: শালি ধান | জিলা: যোৰহাট | উৎপাদন ক্ষমতা: ৫৪.৫ কুইণ্টল/হেক্টৰ")

    def test_validator_ai_lgd_disambiguation_and_closed_enum_guardrail(self):
        ai_ok = _ScriptedAI({"agent3_task": AIResponse({"location_id": "LGD_AS_282", "reason": "Silchar is in Cachar"}, "{}", "groq", "openai/gpt-oss-20b", 85, 190.0, False)})
        norm, tok, _ = ZeroFabricationValidator(ai_runtime=ai_ok).validate_record(_sample_record(district_raw="Silchar"))
        self.assertEqual(norm["location_id"], "LGD_AS_282")
        self.assertEqual(norm["canonical_district"], "Cachar")
        self.assertIn("AI_LGD_Disambiguated", norm["trajectory"])

        ai_bad = _ScriptedAI({"agent3_task": AIResponse({"location_id": "LGD_AS_999", "reason": "invented"}, "{}", "groq", "openai/gpt-oss-20b", 40, 100.0, False)})
        norm_bad, _, _ = ZeroFabricationValidator(ai_runtime=ai_bad).validate_record(_sample_record(district_raw="UnknownTown"))
        self.assertTrue(norm_bad["location_id"].startswith("LGD_AS_UNMAPPED_"))

    def test_validator_ai_critic_grounded_repair_and_hallucination_block(self):
        rec_noisy = _sample_record(raw_unit="quintals per hectare", verbatim_quote="Jorhat Rice Potential_Yield: 54.5 quintals per hectare in 2025-26")
        ai_rep = _ScriptedAI({"agent3_task": AIResponse({"action": "REPAIR", "raw_value": "54.5", "raw_unit": "q/ha", "reason": "ok"}, "{}", "groq", "openai/gpt-oss-20b", 95, 210.0, False)})
        norm, _, _ = ZeroFabricationValidator(ai_runtime=ai_rep).validate_record(rec_noisy)
        self.assertEqual(norm["normalized_value"], 5450.0)
        self.assertEqual(norm["validation_status"], "SELF_CORRECTED")

        ai_hal = _ScriptedAI({"agent3_task": AIResponse({"action": "REPAIR", "raw_value": "999.0", "raw_unit": "q/ha", "reason": "guessed"}, "{}", "groq", "openai/gpt-oss-20b", 50, 100.0, False)})
        with self.assertRaises(ValueError): ZeroFabricationValidator(ai_runtime=ai_hal).validate_record(rec_noisy)
        with self.assertRaises(ValueError): ZeroFabricationValidator(ai_runtime=_ScriptedAI({})).validate_record(_sample_record(raw_value="19.5", raw_unit="pH", metric_name="Soil_pH", verbatim_quote="Soil pH: 19.5"))

    def test_pipeline_fault_isolation_triage_and_sha256_idempotency(self):
        with tempfile.TemporaryDirectory() as td:
            db_path, csv_path, html_404 = os.path.join(td, "sot.db"), os.path.join(td, "f1.csv"), os.path.join(td, "404.html")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("crop_name,variety_name,district_raw,time_period,metric_name,raw_value,raw_unit\nRice (Paddy),Sali,Sibsagar,2024-25,Area,114200*,Hectares\nRapeseed & Mustard,TS-38,Nowgong,2024-25,Production,42800,Tonnes\nWheat,DBW-187,Kamrup,2024-25,Yield,34.0,bushels_invalid\n")
            with open(html_404, "w", encoding="utf-8") as f:
                f.write("<html><body><h1>404 Page Not Found</h1></body></html>")
            triage = lambda p: AIResponse({"is_agricultural_data": "404 Page Not Found" not in p, "language": "en", "reason": "triaged"}, "{}", "groq", "openai/gpt-oss-20b", 55, 110.0, False)
            storage = IngestionStorage(db_path=db_path, schema_path="db/schema.sql")
            pipe = SourceOfTruthPipeline(storage=storage, ai_runtime=_ScriptedAI({"agent1_classifier": triage}))
            cfgs = [
                SourceConfig("SRC_01", "CSV", csv_path, "Document_PDF", "csv_feed", "agent2_ingestion"),
                SourceConfig("SRC_02", "Broken", os.path.join(td, "missing.csv"), "Document_PDF", "csv_feed", "agent2_ingestion"),
                SourceConfig("SRC_06", "404", html_404, "Web_Portal", "html_table", "agent2_ingestion"),
            ]
            by_id = {s.source_id: s for s in pipe.run_sources(cfgs, max_workers=3)}
            self.assertEqual((by_id["SRC_01"].fetch_status, by_id["SRC_01"].records_committed, by_id["SRC_01"].records_rejected), ("PARTIAL", 2, 1))
            self.assertEqual(by_id["SRC_02"].fetch_status, "FAILED")
            self.assertEqual(by_id["SRC_06"].fetch_status, "SKIPPED_NON_DATA")
            self.assertEqual(pipe.run_source(cfgs[0]).fetch_status, "NOT_MODIFIED")
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM fact_agricultural_records WHERE source_id='SRC_01'").fetchone()[0], 2)
            conn.close()

    def test_load_sources_from_csv(self):
        cfgs = load_sources_from_csv("docs/source_agent_map.csv")
        self.assertEqual(len(cfgs), 15)

if __name__ == "__main__":
    unittest.main()
