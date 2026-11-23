"""Source Health & Freshness Monitor (ingestion/monitor.py)."""
import argparse, json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ingestion.storage import IngestionStorage

def _parse_iso_utc(ts: Optional[str]) -> Optional[datetime]:
    if not ts: return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).astimezone(timezone.utc)
    except ValueError:
        return None

class SourceHealthMonitor:
    def __init__(self, storage: Optional[IngestionStorage] = None) -> None:
        self.storage = storage or IngestionStorage()
        self.storage.init_schema()

    def get_health_report(self, now_utc: Optional[datetime] = None) -> Dict[str, Any]:
        now = now_utc or datetime.now(timezone.utc)
        rows = self.storage.get_all_source_health()
        items: List[Dict[str, Any]] = []
        counts = {"HEALTHY": 0, "DEGRADED": 0, "UNHEALTHY": 0, "UNKNOWN": 0, "STALE": 0}
        for r in rows:
            interval_min = int(r.get("refresh_interval_minutes") or 1440)
            last_checked = _parse_iso_utc(r.get("last_checked_at_utc"))
            last_changed = _parse_iso_utc(r.get("last_data_changed_at_utc"))
            checked_age = round((now - last_checked).total_seconds() / 60.0, 1) if last_checked else None
            data_age = round((now - last_changed).total_seconds() / 60.0, 1) if last_changed else None
            raw_status = str(r.get("health_status") or "UNKNOWN")
            is_stale = bool(checked_age is not None and checked_age > (2.0 * interval_min))
            eff_status = "DEGRADED" if (raw_status == "HEALTHY" and is_stale) else raw_status
            counts[eff_status] = counts.get(eff_status, 0) + 1
            if is_stale: counts["STALE"] += 1
            items.append({
                "source_id": r["source_id"], "source_name": r["source_name"], "source_group": r["source_group"],
                "assigned_agent": r["assigned_agent"], "health_status": eff_status, "is_stale": is_stale,
                "consecutive_failures": int(r.get("consecutive_failures") or 0), "last_http_status": r.get("last_http_status"),
                "last_checked_at_utc": r.get("last_checked_at_utc"), "last_success_at_utc": r.get("last_success_at_utc"),
                "last_data_changed_at_utc": r.get("last_data_changed_at_utc"), "checked_age_minutes": checked_age,
                "data_age_minutes": data_age, "refresh_interval_minutes": interval_min, "last_error": r.get("last_error"),
            })
        return {"generated_at_utc": now.isoformat(), "total_sources": len(items), "summary_counts": counts, "sources": items}

    def print_report(self, as_json: bool = False) -> Dict[str, Any]:
        report = self.get_health_report()
        if as_json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return report
        c = report["summary_counts"]
        print("=" * 112)
        print(f"AGRIAGENT SOURCE HEALTH MONITOR | Total={report['total_sources']} | HEALTHY={c['HEALTHY']} | DEGRADED={c['DEGRADED']} | UNHEALTHY={c['UNHEALTHY']} | UNKNOWN={c['UNKNOWN']} | STALE={c['STALE']}")
        print("=" * 112)
        print(f"{'SOURCE':<10} {'STATUS':<10} {'STALE':<6} {'FAILS':>5} {'HTTP':<6} {'AGE(m)':>8} {'INT(m)':>7}  LAST ERROR / NAME")
        print("-" * 112)
        for s in report["sources"]:
            http_s = str(s["last_http_status"]) if s["last_http_status"] is not None else "-"
            age_s = f"{s['checked_age_minutes']:.1f}" if s["checked_age_minutes"] is not None else "-"
            detail = s["last_error"] if s["last_error"] else s["source_name"]
            print(f"{s['source_id']:<10} {s['health_status']:<10} {str(s['is_stale']):<6} {s['consecutive_failures']:>5} {http_s:<6} {age_s:>8} {s['refresh_interval_minutes']:>7}  {str(detail)[:48]}")
        print("=" * 112)
        return report

def main() -> None:
    p = argparse.ArgumentParser(description="AgriAgent Source Health & Freshness Monitor")
    p.add_argument("--db", type=str, default="db/assam_agri_phase2.db")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    SourceHealthMonitor(storage=IngestionStorage(db_path=args.db)).print_report(as_json=args.json)

if __name__ == "__main__":
    main()
