"""
AgriAgent Phase 2 Official CLI Entry Point (run.py)
Routes inputs through MultiAgentOrchestrator (Agent1 -> Agent2/2B -> Agent3).
"""

import argparse
from new_pipeline_orchestrator import MultiAgentOrchestrator

def main():
    parser = argparse.ArgumentParser(description="AgriAgent Phase 2 Multi-Agent CLI Runner")
    parser.add_argument("--input", type=str, default=None, help="Path to unseen surprise file or directory")
    parser.add_argument("--inject-fault", action="store_true", help="Trigger live fault injection & SelfCorrectionNode recovery")
    args = parser.parse_args()

    orchestrator = MultiAgentOrchestrator(db_path="db/assam_agri_phase2.db")
    committed, retries = orchestrator.run_pipeline(surprise_input=args.input, inject_fault=args.inject_fault)
    print(f"[SUCCESS] Committed {committed} validated records to db/assam_agri_phase2.db (Retries={retries}) | SQL dump updated in db/dump.sql")

if __name__ == "__main__":
    main()
