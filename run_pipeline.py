"""
AgriAgent Phase 2 Official CLI Entry Point
Routes through MultiAgentOrchestrator (Agent1Classifier -> Agent2/Agent2B -> Agent3TaskNormalizer).
Usage:
  python run.py --input surprise_samples/
  python run.py --inject-fault
"""

import argparse
from new_pipeline_orchestrator import MultiAgentOrchestrator

def main():
    parser = argparse.ArgumentParser(description="AgriAgent Phase 2 Multi-Agent CLI Runner")
    parser.add_argument("--input", type=str, default=None, help="Path to unseen surprise file or directory (PDF, HTML, CSV, JSON, TXT)")
    parser.add_argument("--inject-fault", action="store_true", help="Trigger live fault injection & SelfCorrectionNode recovery")
    args = parser.parse_args()

    orchestrator = MultiAgentOrchestrator(db_path="db/assam_agri_phase2.db")
    committed, retries = orchestrator.run_pipeline(surprise_input=args.input, inject_fault=args.inject_fault)
    print(f"[SUCCESS] Committed {committed} validated records to db/assam_agri_phase2.db (Retries={retries}) | SQL dump updated in db/dump.sql")

if __name__ == "__main__":
    main()
