"""
AgriAgent Phase 2 Official CLI Entry Point (run.py)
Routes inputs through MultiAgentOrchestrator (agent1_classifier -> agent2_ingestion / agent2b_live_gis -> agent3_task).
"""

import argparse
from new_pipeline_orchestrator import MultiAgentOrchestrator


def main():
    parser = argparse.ArgumentParser(description="AgriAgent Phase 2 Multi-Agent CLI Runner")
    parser.add_argument("--input", type=str, default=None, help="Path or URL to unseen surprise file or directory")
    parser.add_argument("--only-input", action="store_true", help="Process only --input without re-running eval/cases")
    parser.add_argument("--inject-fault", action="store_true", help="Trigger live fault injection & SelfCorrectionNode recovery")
    parser.add_argument("--reset-db", action="store_true", help="Cleanly rebuild database before committing")
    args = parser.parse_args()

    orchestrator = MultiAgentOrchestrator(db_path="db/assam_agri_phase2.db")
    committed, retries = orchestrator.run_pipeline(
        surprise_input=args.input,
        inject_fault=args.inject_fault,
        reset_db=args.reset_db,
        only_input=args.only_input,
    )
    print(f"[SUCCESS] Committed {committed} validated records to db/assam_agri_phase2.db (Retries={retries}) | SQL dump updated in db/dump.sql")


if __name__ == "__main__":
    main()