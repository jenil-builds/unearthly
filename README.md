# AgriAgent Phase 2 — Team 3 (Assam Agricultural Knowledge Base)

## 1. Orchestration Architecture (Supervisor-Router StateGraph)
```text
                  +--------------------------------------+
                  |   CLI / Manifest / Surprise Input    |
                  |   (python run.py --input <path>)     |
                  +------------------+-------------------+
                                     |
                                     v
                  +--------------------------------------+
                  |        SupervisorRouter Node         |
                  | (Routes by Document/Web/Mandi/GIS)   |
                  +------------------+-------------------+
                                     |
      +------------------+-----------+-----------+------------------+
      v                  v                       v                  v
+------------+    +--------------+       +---------------+   +---------------+
| TabularPDF |    | WebPortal    |       | LiveMandi     |   | GeoSpatial    |
| Agent      |    | Agent (As/En)|       | Agent (AMIU)  |   | Agent (WMS)   |
+-----+------+    +------+-------+       +-------+-------+   +-------+-------+
      +------------------+-----------+-----------+------------------+
                                     |
                                     v
                  +--------------------------------------+
                  |       SchemaNormalizer_Agent         |
                  | (Assam LGD Map + SI Unit Conversion) |
                  +------------------+-------------------+
                                     |
                         +-----------+-----------+
                         | Footnote / Fault Gate |
                         +-----------+-----------+
                          /                     \
             (Valid)     /                       \ (Has '*' or Fault)
                        v                         v
         +-----------------------------+   +-----------------------------+
         | SQLite DB + dump.sql Commit |   | SelfCorrectionNode (Retry)  |
         +-----------------------------+   +-----------------------------+
```

## 2. Quick-Start Commands for Live Evaluation (Minutes 0-20)

```bash
# 1. Run the 3 unseen surprise inputs (Minute 0-2 & 12-15):
python run.py --input surprise_samples/

# 2. Run a single surprise file:
python run.py --input surprise_samples/surprise_3_assamese_advisory.txt

# 3. Trigger Live Fault Injection & Recovery (Minute 6-15 Block 4):
python run.py --inject-fault

# 4. Run full 32-case Evaluation Benchmark & generate eval/phase2_metrics.csv (M1-M18):
python eval/run_eval.py

# 5. Run Open-Source Tool Comparison Benchmark (Minute 2-6 Block 2):
python tools/benchmark_open_source.py
```

## 3. Repository Structure & Pre-Check Deliverables
- `docs/source_agent_map.csv` : Complete 15-source mapping (M1=1.00, M2=0.867)
- `docs/agents/*.md`          : 5 Individual Agent Cards
- `docs/challenge.md`         : Literature review & empirical tool comparison
- `eval/cases/` & `reference/`: 32 held-out test cases & ground truth (0 training overlap)
- `eval/run_eval.py`          : Reproducible evaluator generating `eval/phase2_metrics.csv`
- `eval/adapter_comparison.csv`: Base Qwen2.5 vs QLoRA adapter comparison (M18)
- `logs/automation_log.csv`   : Per-input automation, retry, latency & token telemetry (M12, M13)
- `db/schema.sql`, `db/dictionary.md`, `db/dump.sql`: Relational schema, rules & SQL dump (M14-M17)
- `data/manifest.csv`         : Corpus manifest with SHA-256 hashes, dates, languages & licenses
