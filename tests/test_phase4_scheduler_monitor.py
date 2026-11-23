"""Phase 4 Unit & Integration Tests."""
import os, sqlite3, subprocess, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from ingestion.models import SourceConfig
from ingestion.monitor import SourceHealthMonitor
from ingestion.pipeline import SourceOfTruthPipeline
from ingestion.scheduler import RefreshScheduler
from ingestion.storage import IngestionStorage

class TestPhase4SchedulerAndMonitor(unittest.TestCase):
    def test_scheduler_due_manual_and_bounded_daemon(self):
        with tempfile.TemporaryDirectory() as td:
            db_path, csv_ok = os.path.join(td, "sched.db"), os.path.join(td, "ok.csv")
            with open(csv_ok, "w", encoding="utf-8") as f:
                f.write("crop_name,variety_name,district_raw,time_period,metric_name,raw_value,raw_unit\nRice (Paddy),Sali,Jorhat,2024-25,Area,50000,Hectares\n")
            pipe = SourceOfTruthPipeline(storage=IngestionStorage(db_path=db_path, schema_path="db/schema.sql"), enable_ai_triage=False)
            sources = [
                SourceConfig("SRC_01", "OK CSV", csv_ok, "Document_PDF", "csv_feed", "agent2_ingestion", refresh_interval_minutes=60),
                SourceConfig("SRC_02", "Missing CSV", os.path.join(td, "nope.csv"), "Document_PDF", "csv_feed", "agent2_ingestion", refresh_interval_minutes=60),
            ]
            sched = RefreshScheduler(pipeline=pipe, sources=sources)
            self.assertEqual([c.source_id for c in sched.get_due_sources()], ["SRC_01", "SRC_02"])
            s1 = {s.source_id: s for s in sched.run_due()}
            self.assertEqual((s1["SRC_01"].fetch_status, s1["SRC_02"].fetch_status), ("UPDATED", "FAILED"))
            self.assertEqual(sched.get_due_sources(), [])
            self.assertEqual(sched.run_manual(source_ids=["SRC_01"], force=True)[0].fetch_status, "UPDATED")
            self.assertEqual(len(sched.run_daemon(poll_seconds=0.0, max_cycles=2)), 2)
            with self.assertRaises(KeyError):
                sched.run_manual(source_ids=["SRC_999"])

    def test_health_monitor_staleness_and_status_counts(self):
        with tempfile.TemporaryDirectory() as td:
            db_path, csv_ok = os.path.join(td, "mon.db"), os.path.join(td, "ok.csv")
            with open(csv_ok, "w", encoding="utf-8") as f:
                f.write("crop_name,variety_name,district_raw,time_period,metric_name,raw_value,raw_unit\nWheat,DBW-187,Kamrup,2025,Area,1200,Hectares\n")
            storage = IngestionStorage(db_path=db_path, schema_path="db/schema.sql")
            pipe = SourceOfTruthPipeline(storage=storage, enable_ai_triage=False)
            pipe.run_source(SourceConfig("SRC_01", "OK", csv_ok, "Document_PDF", "csv_feed", "agent2_ingestion", refresh_interval_minutes=60))
            for _ in range(3):
                pipe.run_source(SourceConfig("SRC_02", "Bad", os.path.join(td, "missing.csv"), "Document_PDF", "csv_feed", "agent2_ingestion", refresh_interval_minutes=60))
            mon = SourceHealthMonitor(storage=storage)
            now_by_id = {s["source_id"]: s for s in mon.get_health_report()["sources"]}
            self.assertEqual((now_by_id["SRC_01"]["health_status"], now_by_id["SRC_02"]["health_status"]), ("HEALTHY", "UNHEALTHY"))
            fut = mon.get_health_report(now_utc=datetime.now(timezone.utc) + timedelta(minutes=180))
            fut_by_id = {s["source_id"]: s for s in fut["sources"]}
            self.assertTrue(fut_by_id["SRC_01"]["is_stale"])
            self.assertEqual(fut_by_id["SRC_01"]["health_status"], "DEGRADED")

    def test_run_single_isolation_fix(self):
        subprocess.run([sys.executable, "run_single.py", "--source", "SRC_01", "--reset-db"], check=True, capture_output=True)
        conn = sqlite3.connect("db/assam_agri_phase2.db")
        distinct = [r[0] for r in conn.execute("SELECT DISTINCT source_id FROM fact_agricultural_records").fetchall()]
        conn.close()
        self.assertEqual(distinct, ["SRC_01"])
        subprocess.run([sys.executable, "run.py", "--reset-db"], check=True, capture_output=True)

if __name__ == "__main__":
    unittest.main()
