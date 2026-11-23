"""Scheduled & Manual Refresh Runner (ingestion/scheduler.py)."""
import argparse, time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from ingestion.models import FetchSummary, SourceConfig
from ingestion.pipeline import SourceOfTruthPipeline, load_sources_from_csv

def _parse_iso_utc(ts: Optional[str]) -> Optional[datetime]:
    if not ts: return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).astimezone(timezone.utc)
    except ValueError:
        return None

class RefreshScheduler:
    def __init__(self, pipeline: Optional[SourceOfTruthPipeline] = None, sources: Optional[List[SourceConfig]] = None, manifest_path: str = "docs/source_agent_map.csv") -> None:
        self.pipeline = pipeline or SourceOfTruthPipeline()
        self.sources = sources if sources is not None else load_sources_from_csv(manifest_path)

    @staticmethod
    def is_source_due(cfg: SourceConfig, health_row: Optional[Dict], now_utc: Optional[datetime] = None) -> bool:
        now = now_utc or datetime.now(timezone.utc)
        if not health_row or not health_row.get("last_checked_at_utc"):
            return True
        last_checked = _parse_iso_utc(health_row.get("last_checked_at_utc"))
        if last_checked is None:
            return True
        interval_min = int(health_row.get("refresh_interval_minutes") or cfg.refresh_interval_minutes)
        return ((now - last_checked).total_seconds() / 60.0) >= interval_min

    def get_due_sources(self, now_utc: Optional[datetime] = None) -> List[SourceConfig]:
        now = now_utc or datetime.now(timezone.utc)
        return [cfg for cfg in self.sources if self.is_source_due(cfg, self.pipeline.storage.get_source_health(cfg.source_id), now_utc=now)]

    def run_due(self, force: bool = False, max_workers: int = 4) -> List[FetchSummary]:
        due = self.sources if force else self.get_due_sources()
        return self.pipeline.run_sources(due, max_workers=max_workers, force=force) if due else []

    def run_manual(self, source_ids: Optional[List[str]] = None, force: bool = True, max_workers: int = 4) -> List[FetchSummary]:
        if source_ids:
            wanted = {s.strip() for s in source_ids if s.strip()}
            selected = [c for c in self.sources if c.source_id in wanted]
            missing = wanted - {c.source_id for c in selected}
            if missing:
                raise KeyError(f"Unknown source_id(s): {', '.join(sorted(missing))}")
        else:
            selected = list(self.sources)
        return self.pipeline.run_sources(selected, max_workers=max_workers, force=force)

    def run_daemon(self, poll_seconds: float = 60.0, max_workers: int = 4, max_cycles: Optional[int] = None) -> List[List[FetchSummary]]:
        all_cycles: List[List[FetchSummary]] = []
        cycle = 0
        try:
            while max_cycles is None or cycle < max_cycles:
                cycle += 1
                summaries = self.run_due(force=False, max_workers=max_workers)
                if max_cycles is not None:
                    all_cycles.append(summaries)
                if max_cycles is not None and cycle >= max_cycles:
                    break
                if poll_seconds > 0:
                    time.sleep(poll_seconds)
        except KeyboardInterrupt:
            pass
        return all_cycles

def print_summaries(summaries: List[FetchSummary]) -> None:
    if not summaries:
        print("[SCHEDULER] No sources were due for refresh.")
        return
    print("=" * 105)
    print(f"{'SOURCE':<10} {'ADAPTER':<18} {'STATUS':<17} {'HTTP':<6} {'EXT':>4} {'COM':>4} {'REJ':>4} {'MS':>8}  ERROR")
    print("-" * 105)
    for s in summaries:
        http_str = str(s.http_status) if s.http_status is not None else "-"
        print(f"{s.source_id:<10} {s.adapter_type:<18} {s.fetch_status:<17} {http_str:<6} {s.records_extracted:>4} {s.records_committed:>4} {s.records_rejected:>4} {s.latency_ms:>8.1f}  {(s.error_message or '')[:45]}")
    print("=" * 105)

def main() -> None:
    p = argparse.ArgumentParser(description="AgriAgent Source-of-Truth Refresh Scheduler")
    p.add_argument("--manifest", type=str, default="docs/source_agent_map.csv")
    p.add_argument("--source", nargs="*", default=None)
    p.add_argument("--all", action="store_true")
    p.add_argument("--run-due", action="store_true")
    p.add_argument("--daemon", action="store_true")
    p.add_argument("--poll-seconds", type=float, default=60.0)
    p.add_argument("--force", action="store_true")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sched = RefreshScheduler(manifest_path=args.manifest)
    if args.daemon:
        print(f"[SCHEDULER] Starting daemon (poll={args.poll_seconds}s, sources={len(sched.sources)})...")
        sched.run_daemon(poll_seconds=args.poll_seconds, max_workers=args.workers)
    elif args.source:
        print_summaries(sched.run_manual(source_ids=args.source, force=args.force, max_workers=args.workers))
    elif args.all:
        print_summaries(sched.run_manual(source_ids=None, force=args.force, max_workers=args.workers))
    else:
        print_summaries(sched.run_due(force=args.force, max_workers=args.workers))

if __name__ == "__main__":
    main()
