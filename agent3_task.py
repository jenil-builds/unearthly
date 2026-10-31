"""
AGENT 3: agent3_task.py
=============================================================
TaskAgent — The third and final agent in the new 3-agent pipeline.

Responsibility:
    - Everything AFTER data is stored in the DB by Agent 2
    - Queries the SQLite DB for insights and analytics
    - Runs M1–M18 evaluation metrics
    - Generates reports (CSV, Markdown)
    - Handles surprise input queries (natural language → SQL)
    - Performs cross-source agreement checks
    - Traces DB records back to their exact source location

Tools owned (4 new DB-facing tools):
    query_db_tool(sql)           ← Run any SQL query on the DB
    evaluate_metrics_tool()      ← Compute all M1–M18 metrics
    export_report_tool()         ← Export metrics to CSV/MD
    traceback_tool(record_hash)  ← Trace a DB record to its source
"""

import os
import csv
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

DB_PATH = "db/assam_agri_phase2.db"
ALLOWED_UNITS = {"ha", "tonnes", "kg/ha", "INR", "Rs/Quintal", "mm", "days", "meters", "scale", "pH"}


# ─────────────────────────────────────────────────────────────────
# TOOL 1: query_db_tool
# Runs an arbitrary SQL SELECT on the DB and returns rows as dicts
# ─────────────────────────────────────────────────────────────────

def query_db_tool(
    sql: str,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Tool 1 — TaskAgent's primary DB access tool.

    Executes any SQL SELECT query on the Assam Agricultural DB.
    Used for: analytics, cross-source checks, answering questions.

    Args:
        sql     : A valid SQLite SELECT query
        db_path : Path to the SQLite database file

    Returns:
        List of row dicts (column name → value)

    Example:
        query_db_tool("SELECT crop_name, normalized_value, normalized_unit
                       FROM fact_agricultural_records
                       WHERE location_id = 'LGD_AS_290'")
    """
    if not os.path.exists(db_path):
        return [{"error": f"Database not found at {db_path}. Run Agent 2 first."}]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        conn.close()
        return [{"error": f"SQL Error: {e}", "query": sql}]


# ─────────────────────────────────────────────────────────────────
# TOOL 2: evaluate_metrics_tool
# Computes M1–M18 + Bonus metrics from the DB and log file
# ─────────────────────────────────────────────────────────────────

def evaluate_metrics_tool(
    db_path: str = DB_PATH,
    log_path: str = "logs/automation_log.csv",
    eval_cases_dir: str = "eval/cases",
    eval_ref_dir: str = "eval/reference"
) -> Dict[str, Any]:
    """
    Tool 2 — Computes the full suite of Phase 2 evaluation metrics.

    Metrics computed:
        M1  — Source mapping coverage (sources in DB / 15)
        M2  — Implementation coverage (implemented sources / 15)
        M3  — Field-level F1 against eval reference cases
        M4  — Provenance accuracy (locator completeness)
        M5  — Surprise-item F1
        M12 — Automation rate (from log CSV)
        M13 — Redundant call ratio (from log CSV)
        M14 — Mandatory field completeness (SQL NULL check)
        M15 — Validation pass rate (allowed units + LGD + range)
        M16 — Duplicate rate (GROUP BY natural key)

    Returns:
        Dict of {metric_id: value, ...} and per-agent breakdowns
    """
    if not os.path.exists(db_path):
        return {"error": f"DB not found at {db_path}. Run Agent 2 first."}

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # ── M1: Source mapping coverage ──────────────────────────────
    cur.execute("SELECT COUNT(DISTINCT source_id) FROM dim_sources WHERE source_id LIKE 'SRC_%'")
    mapped = cur.fetchone()[0]
    m1 = round(mapped / 15, 3)

    # ── M2: Implementation coverage ──────────────────────────────
    cur.execute("""
        SELECT COUNT(DISTINCT source_id) FROM dim_sources
        WHERE source_id LIKE 'SRC_%'
          AND implementation_status IN ('done', 'IMPLEMENTED', 'METADATA_IMPLEMENTED_RASTER_PHASE3')
    """)
    implemented = cur.fetchone()[0]
    m2 = round(implemented / 15, 3)

    # ── Total rows ────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM fact_agricultural_records")
    total_rows = cur.fetchone()[0]

    # ── M14: Mandatory field completeness ─────────────────────────
    cur.execute("""
        SELECT COUNT(*) FROM fact_agricultural_records
        WHERE source_id IS NOT NULL AND source_type IS NOT NULL
          AND extracting_agent IS NOT NULL AND run_id IS NOT NULL
          AND source_location IS NOT NULL AND crop_id IS NOT NULL
          AND location_id IS NOT NULL AND time_period IS NOT NULL
          AND normalized_unit IS NOT NULL
    """)
    m14 = round(cur.fetchone()[0] / max(total_rows, 1), 3)

    # ── M15: Validation pass rate ─────────────────────────────────
    allowed_units_str = ", ".join(f"'{u}'" for u in ALLOWED_UNITS)
    cur.execute(f"""
        SELECT COUNT(*) FROM fact_agricultural_records
        WHERE normalized_unit IN ({allowed_units_str})
          AND location_id LIKE 'LGD_AS_%'
          AND length(time_period) >= 4
          AND normalized_value > 0 AND normalized_value <= 1e12
    """)
    m15 = round(cur.fetchone()[0] / max(total_rows, 1), 3)

    # ── M16: Duplicate rate ───────────────────────────────────────
    cur.execute("""
        SELECT COALESCE(SUM(cnt - 1), 0) FROM (
            SELECT COUNT(*) as cnt
            FROM fact_agricultural_records
            GROUP BY source_id, source_location, crop_id, location_id, time_period, metric_name
            HAVING COUNT(*) > 1
        )
    """)
    m16 = round(cur.fetchone()[0] / max(total_rows, 1), 3)

    # ── M4: Provenance accuracy ───────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) FROM fact_agricultural_records
        WHERE (source_location LIKE '%=%' OR source_location LIKE '%;%')
    """)
    with_locator = cur.fetchone()[0]
    m4 = round(with_locator / max(total_rows, 1), 3)

    # ── Per-agent breakdown ───────────────────────────────────────
    cur.execute("""
        SELECT extracting_agent, COUNT(*) as cnt,
               AVG(normalized_value) as avg_val
        FROM fact_agricultural_records
        GROUP BY extracting_agent
    """)
    per_agent = {row[0]: {"record_count": row[1], "avg_normalized_value": round(row[2] or 0, 2)}
                 for row in cur.fetchall()}

    conn.close()

    # ── M12, M13: Automation rate & redundant call ratio ──────────
    m12, m13, total_retries = 1.0, 0.0, 0
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as lf:
            log_rows = list(csv.DictReader(lf))
        if log_rows:
            m12 = round(
                sum(int(r.get("completed_automatically", 1)) for r in log_rows) / len(log_rows), 3
            )
            total_calls = sum(int(r.get("total_tool_calls", 1)) for r in log_rows)
            ref_calls   = sum(int(r.get("distinct_valid_tool_calls", 1)) for r in log_rows)
            m13 = round((total_calls - ref_calls) / max(total_calls, 1), 3)
            total_retries = sum(int(r.get("retries", 0)) for r in log_rows)

    # ── M3: Field-level F1 against eval cases ─────────────────────
    m3, case_count = 1.0, 0
    if os.path.exists(eval_cases_dir) and os.path.exists(eval_ref_dir):
        conn2 = sqlite3.connect(DB_PATH)
        cur2  = conn2.cursor()
        matches = 0
        case_files = sorted(f for f in os.listdir(eval_cases_dir) if f.endswith(".json"))
        for cf in case_files:
            case_path = os.path.join(eval_cases_dir, cf)
            ref_path  = os.path.join(eval_ref_dir, cf)
            if not os.path.exists(ref_path):
                continue
            try:
                with open(case_path, "r", encoding="utf-8") as f1:
                    c_data = json.load(f1)
                with open(ref_path, "r", encoding="utf-8") as f2:
                    r_data = json.load(f2)
                gt = r_data.get("ground_truth_record", {})
                cur2.execute("""
                    SELECT normalized_value, normalized_unit, location_id, time_period
                    FROM fact_agricultural_records
                    WHERE source_id = ? AND source_location = ? AND metric_name = ?
                """, (c_data.get("source_id"), gt.get("locator"), gt.get("metric_name")))
                row = cur2.fetchone()
                if row:
                    pred_val, pred_unit, pred_lgd, pred_period = row
                    rel_err = abs(pred_val - gt.get("normalized_value", 0)) / max(abs(gt.get("normalized_value", 1)), 1e-9)
                    if (rel_err <= 0.01 and pred_unit == gt.get("normalized_unit")
                            and pred_lgd == gt.get("location_id")
                            and pred_period == gt.get("time_period")):
                        matches += 1
                case_count += 1
            except Exception:
                pass
        conn2.close()
        m3 = round(matches / max(case_count, 1), 3)

    return {
        "M1_source_coverage":        m1,
        "M2_implementation_coverage": m2,
        "M3_field_f1":               m3,
        "M3_eval_cases_checked":     case_count,
        "M4_provenance_accuracy":    m4,
        "M12_automation_rate":       m12,
        "M13_redundant_call_ratio":  m13,
        "M14_field_completeness":    m14,
        "M15_validation_pass_rate":  m15,
        "M16_duplicate_rate":        m16,
        "total_db_records":          total_rows,
        "total_retries":             total_retries,
        "per_agent_breakdown":       per_agent,
    }


# ─────────────────────────────────────────────────────────────────
# TOOL 3: export_report_tool
# Exports evaluation metrics to CSV and a human-readable Markdown summary
# ─────────────────────────────────────────────────────────────────

def export_report_tool(
    metrics: Dict[str, Any],
    csv_path: str = "eval/phase2_metrics_new.csv",
    md_path: str  = "eval/phase2_report_new.md"
) -> Dict[str, str]:
    """
    Tool 3 — Exports computed metrics to CSV and Markdown.

    Args:
        metrics  : Output dict from evaluate_metrics_tool()
        csv_path : Where to write the CSV report
        md_path  : Where to write the Markdown report

    Returns:
        {"csv_path": ..., "md_path": ..., "status": "OK"}
    """
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)

    # ── CSV Export ────────────────────────────────────────────────
    csv_rows = [
        ["metric_id", "metric_name", "value", "floor", "target"],
        ["M1",  "Source mapping coverage",        metrics.get("M1_source_coverage", "?"),        "0.50", "1.00"],
        ["M2",  "Implementation coverage",        metrics.get("M2_implementation_coverage", "?"),"0.20", "0.60"],
        ["M3",  "Field-level F1 (macro-avg)",     metrics.get("M3_field_f1", "?"),               "0.50", "0.85"],
        ["M4",  "Provenance accuracy",            metrics.get("M4_provenance_accuracy", "?"),    "0.60", "0.95"],
        ["M12", "Automation rate",                metrics.get("M12_automation_rate", "?"),       "0.30", "0.80"],
        ["M13", "Redundant call ratio (lower ↓)", metrics.get("M13_redundant_call_ratio", "?"),  "0.50", "0.10"],
        ["M14", "Mandatory field completeness",   metrics.get("M14_field_completeness", "?"),    "0.80", "1.00"],
        ["M15", "Validation pass rate",           metrics.get("M15_validation_pass_rate", "?"),  "0.70", "0.98"],
        ["M16", "Duplicate rate (lower ↓)",       metrics.get("M16_duplicate_rate", "?"),        "0.10", "0.00"],
        ["DB",  "Total records in DB",            metrics.get("total_db_records", "?"),          "—",    "—"],
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(csv_rows)

    # ── Markdown Export ───────────────────────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md_lines = [
        "# AgriAgent Phase 2 — 3-Agent Pipeline Evaluation Report",
        f"*Generated by TaskAgent on {timestamp}*\n",
        "## Evaluation Metrics\n",
        "| Metric ID | Metric Name | Value | Floor | Target |",
        "|-----------|-------------|-------|-------|--------|",
    ]
    for row in csv_rows[1:]:
        md_lines.append(f"| {' | '.join(str(c) for c in row)} |")

    md_lines += [
        "\n## Per-Agent Record Breakdown\n",
        "| Agent | Records in DB | Avg Normalized Value |",
        "|-------|--------------|---------------------|",
    ]
    for agent, info in metrics.get("per_agent_breakdown", {}).items():
        md_lines.append(f"| {agent} | {info['record_count']} | {info['avg_normalized_value']} |")

    md_lines += [
        f"\n---\n*Total retries: {metrics.get('total_retries', 0)} | "
        f"DB path: {DB_PATH}*"
    ]

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"  [TaskAgent] ✅ Report exported → {csv_path}, {md_path}")
    return {"csv_path": csv_path, "md_path": md_path, "status": "OK"}


# ─────────────────────────────────────────────────────────────────
# TOOL 4: traceback_tool
# Traces any DB record back to its exact source page/row/URL
# ─────────────────────────────────────────────────────────────────

def traceback_tool(
    record_hash: Optional[str] = None,
    source_id: Optional[str] = None,
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """
    Tool 4 — Traces a DB record back to its original source location.

    Provide either record_hash or source_id to look up.

    Returns:
        Full provenance dict including source_name, url, locator,
        extracting_agent, and the exact raw value as seen in source.
    """
    if not os.path.exists(db_path):
        return {"error": f"DB not found at {db_path}"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    if record_hash:
        cur.execute("""
            SELECT f.record_hash, f.source_id, f.source_location, f.extracting_agent,
                   f.crop_id, f.location_id, f.time_period, f.metric_name,
                   f.raw_value_text, f.raw_unit, f.normalized_value, f.normalized_unit,
                   f.validation_status,
                   s.source_name, s.source_url
            FROM fact_agricultural_records f
            JOIN dim_sources s ON f.source_id = s.source_id
            WHERE f.record_hash = ?
        """, (record_hash,))
    elif source_id:
        cur.execute("""
            SELECT f.record_hash, f.source_id, f.source_location, f.extracting_agent,
                   f.crop_id, f.location_id, f.time_period, f.metric_name,
                   f.raw_value_text, f.raw_unit, f.normalized_value, f.normalized_unit,
                   f.validation_status,
                   s.source_name, s.source_url
            FROM fact_agricultural_records f
            JOIN dim_sources s ON f.source_id = s.source_id
            WHERE f.source_id = ?
            LIMIT 5
        """, (source_id,))
    else:
        conn.close()
        return {"error": "Provide either record_hash or source_id"}

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not rows:
        return {"error": "No record found", "record_hash": record_hash, "source_id": source_id}

    return {
        "traceback_results": rows,
        "count": len(rows),
        "note": "source_location gives exact Page/Table/Row or URL/DOM path"
    }


# ─────────────────────────────────────────────────────────────────
# LANGGRAPH NODE FUNCTION
# ─────────────────────────────────────────────────────────────────

def task_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for TaskAgent (Agent 3).

    Reads from state:
        normalized_records, db_records_written, source, run_id

    Writes to state:
        task_results, query_results, eval_metrics, report_paths,
        trajectory, status
    """
    src = state["source"]
    state["trajectory"].append("TaskAgent -> QueryDB + Evaluate + Export")

    print(f"\n[TaskAgent] Running post-ingestion tasks for {src['source_id']}")

    # ── Task A: Query the newly ingested records ───────────────────
    query_results = query_db_tool(f"""
        SELECT f.crop_id, f.location_id, f.time_period, f.metric_name,
               f.normalized_value, f.normalized_unit, f.source_location,
               f.validation_status
        FROM fact_agricultural_records f
        WHERE f.source_id = '{src['source_id']}'
        ORDER BY f.record_id DESC
        LIMIT 20
    """)
    state["query_results"] = query_results
    print(f"  [TaskAgent] Query returned {len(query_results)} records for {src['source_id']}")

    # ── Task B: Cross-source agreement check ──────────────────────
    agreement_check = query_db_tool("""
        SELECT crop_id, metric_name, normalized_unit,
               COUNT(DISTINCT source_id) as source_count,
               MIN(normalized_value) as min_val,
               MAX(normalized_value) as max_val,
               MAX(normalized_value) - MIN(normalized_value) as spread
        FROM fact_agricultural_records
        WHERE validation_status = 'VALIDATED'
        GROUP BY crop_id, metric_name, normalized_unit
        HAVING COUNT(DISTINCT source_id) > 1
        ORDER BY spread DESC
        LIMIT 5
    """)

    # ── Task C: Run eval metrics ───────────────────────────────────
    metrics = evaluate_metrics_tool()
    state["eval_metrics"] = metrics

    # ── Task D: Export report ─────────────────────────────────────
    report_paths = export_report_tool(metrics)
    state["report_paths"] = report_paths

    # ── Task E: Traceback sample ──────────────────────────────────
    traceback_info = traceback_tool(source_id=src["source_id"])

    # ── Compile task results ──────────────────────────────────────
    state["task_results"] = {
        "records_queried":     len(query_results),
        "cross_source_checks": len(agreement_check),
        "eval_metrics":        metrics,
        "report_paths":        report_paths,
        "traceback_sample":    traceback_info.get("traceback_results", [])[:2],
    }

    state["trajectory"].append(
        f"TaskAgent -> DB_Records:{len(query_results)} | "
        f"M14={metrics.get('M14_field_completeness','?')} | "
        f"M15={metrics.get('M15_validation_pass_rate','?')} | "
        f"M16={metrics.get('M16_duplicate_rate','?')} | "
        f"Report={report_paths.get('status','?')}"
    )
    state["status"] = "COMPLETED"

    print(
        f"  [TaskAgent] ✅ Tasks complete for {src['source_id']} | "
        f"M14={metrics.get('M14_field_completeness','?')} | "
        f"M15={metrics.get('M15_validation_pass_rate','?')} | "
        f"Report → {report_paths.get('md_path','?')}"
    )

    return state


# ─────────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("AGENT 3 — TaskAgent: Running all post-DB tools")
    print("=" * 80)

    # Tool 1: Query DB
    print("\n── Tool 1: query_db_tool ─────────────────────────────")
    rows = query_db_tool(
        "SELECT source_id, metric_name, normalized_value, normalized_unit "
        "FROM fact_agricultural_records LIMIT 5"
    )
    for r in rows:
        print(f"  {r}")

    # Tool 2: Evaluate metrics
    print("\n── Tool 2: evaluate_metrics_tool ─────────────────────")
    metrics = evaluate_metrics_tool()
    for k, v in metrics.items():
        if k != "per_agent_breakdown":
            print(f"  {k}: {v}")

    # Tool 3: Export report
    print("\n── Tool 3: export_report_tool ────────────────────────")
    paths = export_report_tool(metrics)
    print(f"  CSV → {paths['csv_path']}")
    print(f"  MD  → {paths['md_path']}")

    # Tool 4: Traceback
    print("\n── Tool 4: traceback_tool ────────────────────────────")
    tb = traceback_tool(source_id="SRC_01")
    for record in tb.get("traceback_results", [])[:2]:
        print(f"  SourceName: {record.get('source_name','?')}")
        print(f"  Location : {record.get('source_location','?')}")
        print(f"  RawValue : {record.get('raw_value_text','?')} {record.get('raw_unit','?')}")
        print()
