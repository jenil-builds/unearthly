# Agent Card: `agent1_classifier` (`Agent1Classifier`)

* **Module File:** `agent1_classifier.py`
* **Assigned Sources:** All 15 manifest sources (`SRC_01`–`SRC_15`) and all unseen surprise inputs (`.pdf`, `.csv`, `.html`, `.txt`, `.json`).
* **Core Responsibility:** Inspects incoming file paths, extensions, `source_group` metadata, URL patterns, and UTF-8 Assamese Unicode ranges (`\u0980–\u09FF`) to classify source modality, detect language (`en` vs. `as`), and route execution to the appropriate specialist ingestion agent (`agent2_ingestion` or `agent2b_live_gis`).
* **Inputs & Expected Outputs:**
  * **Input:** `source_meta` dictionary containing `filepath`, `source_group`, `expected_agent`, `language`, or `raw_text_sample`.
  * **Output:** Structured routing dictionary containing `routing_agent` (`"agent1_classifier"`), `target_agent` (`"agent2_ingestion"` or `"agent2b_live_gis"`), `selected_tool`, `source_type`, `language`, `modality`, and `tool_args_valid`.
* **Models & Tools Used (with Justification):**
  * **Deterministic Rule Engine + Regex Unicode Detector:** Uses deterministic dispatch over file extensions and source groups to guarantee $100\%$ tool-selection accuracy (`M6 = 1.000`) and zero routing latency, while flagging Assamese script (`[\u0980-\u09FF]`) for bilingual semantic extraction.
  * **AI Classifier Hook:** `Qwen/Qwen2.5-72B-Instruct` metadata tagger for ambiguous or extensionless streams.
* **Implementation Status & Known Limitations:**
  * **Status:** `done` (100% implemented and unit-tested in `test_all_agents.py`).
  * **Limitations:** Extensionless binary files without `source_group` metadata default to `Document_PDF` routing.

---

## Live Ingestion Upgrade (`ingestion/pipeline.py`)
* Strips HTML `<head>`, `<script>`, `<style>`, and `<noscript>` boilerplate before LLM triage (`_build_triage_preview`).
* Calls `AIRuntime` (`AGENT1_MODEL`, default `openai/gpt-oss-20b`) to detect 404/login/navigation pages and short-circuit them as `SKIPPED_NON_DATA` (marked `DEGRADED` in `source_health` without caching non-data hashes).
