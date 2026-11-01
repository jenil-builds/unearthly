# AgriAgent Phase 2 — Team 3 (Assam Agricultural Knowledge Base)

## 1. Multi-Agent Architecture (`MultiAgentOrchestrator`)

Our Phase 2 system implements a decoupled, concurrent 4-module multi-agent pipeline (`new_pipeline_orchestrator.py`) that routes, extracts, self-corrects, and normalizes multi-modal Assam agricultural sources into an idempotent SQLite star-schema (`db/assam_agri_phase2.db`).

```text
                  +-----------------------------------------------+
                  |     CLI / Manifest / Surprise Input Files     |
                  |     (python run.py --input <file_or_dir>)     |
                  +-----------------------+-----------------------+
                                          |
                                          v
                  +-----------------------------------------------+
                  |      Agent 1: agent1_classifier.py            |
                  |  (Modality, Extension & Assamese Script       |
                  |   Detection: \u0980-\u09FF -> Target Router)  |
                  +-----------------------+-----------------------+
                                          |
               +--------------------------+--------------------------+
               | (Document_PDF / Web_Portal)                         | (Database_Dashboard / Geospatial_GIS)
               v                                                     v
+--------------------------------------+             +--------------------------------------+
|     Agent 2: agent2_ingestion.py     |             |    Agent 2B: agent2b_live_gis.py     |
|  - TabularPDF role (pdfplumber/CSV)  |             |  - LiveMandi role (AMIU Jorhat DOM)  |
|  - WebPortal role (BS4 + Assamese)   |             |  - GeoSpatial role (WMS/Layer Meta)  |
|  - AISemanticExtractor (Qwen2.5-72B) |             +-------------------+------------------+
+------------------+-------------------+                                 |
                   +--------------------------+--------------------------+
                                              |
                                              v
                  +-----------------------------------------------+
                  |         Agent 3: agent3_task.py               |
                  |  - SelfCorrectionNode (Strips '*' & NaN)      |
                  |  - Assam LGD Resolver (35+ aliases -> LGD_AS) |
                  |  - SI Unit Standardizer (q/ha -> kg/ha, etc.) |
                  |  - Natural-Key & SHA-256 Deduplication        |
                  +-----------------------+-----------------------+
                                          |
                                          v
                  +-----------------------------------------------+
                  |    SQLite Star-Schema (db/assam_agri_phase2)  |
                  |    + Reproducible SQL Dump (db/dump.sql)      |
                  +-----------------------------------------------+
```

---

## 2. Quick-Start Commands for Live Evaluation & Defense

```bash
# 1. Run unit tests across all 4 independent agent modules:
python test_all_agents.py

# 2. Run the full 32-case held-out benchmark + surprise suite (generates eval/phase2_metrics.csv):
python eval/run_eval.py

# 3. Run unseen surprise inputs (CSV, HTML, PDF, or Assamese TXT):
python run.py --input surprise_samples/

# 4. Run a single source from the 15-source manifest (isolated execution):
python run_single.py --source SRC_01 --reset-db

# 5. Trigger live fault injection & SelfCorrectionNode recovery:
python run.py --inject-fault

# 6. Run live provenance trace-back on 3 random database records (Metric M17):
python tools/inspect_row_provenance.py

# 7. Run empirical open-source PDF extraction benchmark (Section 2 challenge):
python tools/benchmark_open_source.py
```

---

## 3. Repository Structure & Protocol Deliverables

| Deliverable Path | Protocol Role & Metrics Covered |
| :--- | :--- |
| `agent1_classifier.py` | **Agent 1 (`Agent1Classifier`)**: Modality router & tool selector (`M6`, `M7`). |
| `agent2_ingestion.py` | **Agent 2 (`Agent2Ingestion` & `AISemanticExtractor`)**: PDF, CSV, HTML & Assamese text extraction (`M3`, `M5`). |
| `agent2b_live_gis.py` | **Agent 2B (`Agent2BLiveGIS`)**: AMIU Live Mandi & Web-GIS metadata extraction (`M3`, `M9`). |
| `agent3_task.py` | **Agent 3 (`Agent3TaskNormalizer`)**: Self-correction node, LGD mapping, SI unit conversion (`M8`, `M14`–`M16`). |
| `new_pipeline_orchestrator.py` | **Orchestrator (`MultiAgentOrchestrator`)**: Concurrent `ThreadPoolExecutor` pipeline & SQLite commit engine (`M11`–`M13`). |
| `docs/source_agent_map.csv` | Complete 15-source mapping table (`M1 = 1.000`, `M2 = 1.000`). |
| `docs/challenge.md` | Deep dive into multi-header PDF & Assamese entity resolution challenges + literature review. |
| `docs/agents/*.md` | Individual Agent Cards detailing inputs, outputs, tools, models, and limitations. |
| `eval/cases/` & `eval/reference/` | 32 held-out test cases and ground-truth references (`0` SHA-256 overlap with SFT split). |
| `eval/run_eval.py` | Official evaluation suite producing `eval/phase2_metrics.csv` (`M1`–`M18` + Bonus). |
| `eval/adapter_comparison.csv` | Base `Qwen2.5-7B-Instruct` vs. `Qwen2.5-7B-AssamAgri-QLoRA` comparison (`M18 = +0.066`). |
| `db/schema.sql` & `db/dictionary.md` | Relational DDL with `CHECK` & composite `UNIQUE` natural-key constraints + data dictionary. |
| `db/assam_agri_phase2.db` & `db/dump.sql` | Populated SQLite database and full SQL dump (`38` validated records, `0` duplicates). |
| `logs/automation_log.csv` | Per-run telemetry logging automation status, retries, latency (ms), tokens, and trajectories. |