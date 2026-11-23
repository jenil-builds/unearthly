"""AgriAgent Phase 2 Official CLI Entry Point (run.py)."""
import argparse
from new_pipeline_orchestrator import MultiAgentOrchestrator

def main():
    parser = argparse.ArgumentParser(description="AgriAgent Phase 2 Multi-Agent & Source-of-Truth CLI Runner")
    parser.add_argument("--input", type=str, default=None, help="Path or URL to unseen surprise file or directory")
    parser.add_argument("--only-input", action="store_true", help="Process only --input without re-running eval/cases")
    parser.add_argument("--inject-fault", action="store_true", help="Trigger live fault injection & SelfCorrectionNode recovery")
    parser.add_argument("--reset-db", action="store_true", help="Cleanly rebuild database before committing")
    parser.add_argument("--refresh-all", action="store_true", help="Manually refresh all external sources in docs/source_agent_map.csv")
    parser.add_argument("--refresh-source", nargs="+", default=None, help="Manually refresh specific source_id(s)")
    parser.add_argument("--refresh-due", action="store_true", help="Run a single scheduled pass for due sources (cron-friendly)")
    parser.add_argument("--schedule", action="store_true", help="Run continuous scheduled refresh daemon")
    parser.add_argument("--poll-seconds", type=float, default=60.0, help="Daemon polling interval in seconds")
    parser.add_argument("--force", action="store_true", help="Bypass ETag/SHA-256 cache during source refresh")
    parser.add_argument("--source-health", action="store_true", help="Display source health and freshness report")
    parser.add_argument("--json", action="store_true", help="Print health report as JSON")
    args = parser.parse_args()

    if args.source_health:
        from ingestion.monitor import SourceHealthMonitor
        SourceHealthMonitor().print_report(as_json=args.json)
        return

    if args.refresh_all or args.refresh_source or args.refresh_due or args.schedule:
        from ingestion.scheduler import RefreshScheduler, print_summaries
        sched = RefreshScheduler()
        if args.schedule:
            print(f"[SCHEDULER] Starting scheduled refresh daemon (poll={args.poll_seconds}s)...")
            sched.run_daemon(poll_seconds=args.poll_seconds)
        elif args.refresh_source:
            print_summaries(sched.run_manual(source_ids=args.refresh_source, force=args.force))
        elif args.refresh_all:
            print_summaries(sched.run_manual(source_ids=None, force=args.force))
        else:
            print_summaries(sched.run_due(force=args.force))
        return

    orchestrator = MultiAgentOrchestrator(db_path="db/assam_agri_phase2.db")
    committed, retries = orchestrator.run_pipeline(
        surprise_input=args.input, inject_fault=args.inject_fault, reset_db=args.reset_db, only_input=args.only_input,
    )
    print(f"[SUCCESS] Committed {committed} validated records to db/assam_agri_phase2.db (Retries={retries}) | SQL dump updated in db/dump.sql")

if __name__ == "__main__":
    main()
