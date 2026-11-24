# AgriAgents Assam - Multi-Agent & Source-of-Truth Agricultural Knowledge Base

A production-grade, fault-isolated multi-agent ingestion and normalization system for Assam agricultural data (English & Assamese). Combines LLM-assisted triage, schema mapping, and entity disambiguation with deterministic **zero-fabrication grounding gates** and WAL-mode SQLite persistence.

---

## 1. Architecture Overview

### A. Source-of-Truth Live Ingestion Pipeline (`ingestion/`)
```text
[docs/source_agent_map.csv (15 Assam Sources)]
        |
        v
RefreshScheduler (--refresh-all | --refresh-source | --refresh-due | --schedule)
        |  Per-Source Fault Isolation (ThreadPoolExecutor)
        v
SafeHTTPClient (Redirect-Safe SSRF Check, ETag/304, 25 MB Cap, SHA-256)
        |
        v
Agent 1 AI Triage (HTML boilerplate stripping -> SKIPPED_NON_DATA on 404/login/nav)
        |
        v
Modular Adapters (csv_feed | html_table | pdf_table | unstructured_text | wms_gis)
  +-- AISchemaMapper (AI Schema-Once Table Mapping + Citation-Anchored Extractive LLM)
        |
        v
VerbatimGroundingGate (Decimal-aware numeric boundaries + structured-table verification)
        |
        v
ZeroFabricationValidator (Agent 3)
  |-- Deterministic SI Unit & LGD Normalization (agent3_task.py: q/ha, t/ha, Rs. Lakh, etc.)
  |-- Constrained AI LGD Disambiguation (Closed 35-District Assam LGD Catalog)
  +-- Grounded AI Critic (Unit-coercion blocking, agronomic bounds, per-batch call cap)
        |
        v
SQLite WAL Storage (fact_agricultural_records, extraction_runs, source_fetch_log, source_health)
```

### B. Phase 2 Evaluation Pipeline (`MultiAgentOrchestrator`)
`new_pipeline_orchestrator.py` routes held-out benchmark cases (`eval/cases/`) and unseen surprise files (`--input`) through `agent1_classifier.py` -> `agent2_ingestion.py` / `agent2b_live_gis.py` -> `agent3_task.py`, committing to `db/assam_agri_phase2.db` and exporting `db/dump.sql` + `logs/automation_log.csv`.

---

## 2. Setup & Configuration

```bash
pip install -r requirements.txt
cp .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
```

Add your `GROQ_API_KEY` (or another OpenAI-compatible provider key) to `.env`, then verify connectivity:
```bash
python -c "from ingestion.ai_runtime import AIRuntime; rt = AIRuntime(); print(rt.call_json('agent1_classifier', 'Return JSON only.', 'Return a JSON object with key status set to ok'))"
```

---

## 3. Quick-Start CLI Commands

### Live Source-of-Truth Refresh & Health Monitoring
```bash
# Manually refresh specific sources:
python run.py --refresh-source SRC_02 SRC_11 --force

# Manually refresh all 15 registered sources (fault-isolated):
python run.py --refresh-all

# Refresh a single source live via run_single.py:
python run_single.py --source SRC_02 --live --force

# Cron-friendly scheduled pass (refreshes only due sources):
python run.py --refresh-due

# Continuous scheduled daemon:
python run.py --schedule --poll-seconds 300

# View source health & freshness report (table or JSON):
python run.py --source-health
python run.py --source-health --json
```

### Testing & Phase 2 Evaluation
```bash
# Run full unit, integration & FSM hardening test suite (19 tests):
python -m unittest discover -s tests -v

# Run 32-case held-out benchmark (generates eval/phase2_metrics.csv):
python eval/run_eval.py

# Run isolated single-source evaluation commit:
python run_single.py --source SRC_01 --reset-db

# Trigger live fault injection & SelfCorrectionNode recovery:
python run.py --inject-fault

# Inspect database row provenance (Metric M17):
python tools/inspect_row_provenance.py
```

---

## 4. Repository Structure

| Path | Description |
| :--- | :--- |
| `run.py`, `run_single.py` | Official CLI entry points for live source-of-truth refreshes and Phase 2 evaluation. |
| `ingestion/config.py`, `ai_runtime.py` | Zero-dependency `.env` loader, per-agent model routing, provider failover, and JSON extraction. |
| `ingestion/http_client.py` | Redirect-safe SSRF-protected HTTP/local fetch client (`ETag`/`304`, 25 MB cap, SHA-256). |
| `ingestion/base_adapter.py`, `adapters/` | `BaseSourceAdapter`, `AdapterRegistry`, `AISchemaMapper`, and 5 isolated connectors (`csv_feed`, `html_table`, `pdf_table`, `unstructured_text`, `wms_gis`). |
| `ingestion/grounding.py`, `validator.py` | `VerbatimGroundingGate`, constrained 35-district AI LGD disambiguator, and unit-coercion-safe AI Critic. |
| `ingestion/pipeline.py`, `storage.py` | Fault-isolated `SourceOfTruthPipeline` and WAL-mode SQLite persistence with `BEGIN IMMEDIATE` transactions. |
| `ingestion/scheduler.py`, `monitor.py` | Manual/cron/daemon refresh scheduler and `HEALTHY`/`DEGRADED`/`UNHEALTHY`/staleness health monitor. |
| `agent1_classifier.py`, `agent2_ingestion.py`, `agent2b_live_gis.py`, `agent3_task.py` | Core 4-agent modules for classification, extraction, live/GIS parsing, and deterministic normalization. |
| `new_pipeline_orchestrator.py` | Concurrent Phase 2 evaluation orchestrator. |
| `db/` | `schema.sql` (7 tables), `dictionary.md`, `assam_agri_phase2.db`, and `dump.sql`. |
| `docs/` | `source_agent_map.csv`, `challenge.md`, and individual Agent Cards (`docs/agents/*.md`). |
| `eval/` | 32 held-out cases (`cases/`, `reference/`), `run_eval.py`, `phase2_metrics.csv`, and `adapter_comparison.csv`. |
| `tests/` | 19 unit, integration, and FSM hardening tests (`test_phase2` through `test_phase5`). |
| `tools/` | `inspect_row_provenance.py` and `benchmark_open_source.py`. |

---

## 5. Adding a New Source Connector

1. Subclass `BaseSourceAdapter` (`ingestion/base_adapter.py`) in `ingestion/adapters/` with a unique `adapter_type`.
2. Implement `fetch()` (via `SafeHTTPClient`) and `parse()` (via `AISchemaMapper`).
3. Register the class in `build_default_registry()` (`ingestion/adapters/__init__.py`).
4. Add the source to `docs/source_agent_map.csv` and add an isolated unit test in `tests/`.
