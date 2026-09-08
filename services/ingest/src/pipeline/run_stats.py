"""Run-level observability: counters, source distribution, summary payload."""

import json
from typing import Dict, List, Optional

from infra.metrics import cost_tracker
from selection.models import NewsItem


def bump_run_stat(run_stats: Optional[Dict[str, int]], key: str) -> None:
    if run_stats is not None:
        run_stats[key] = run_stats.get(key, 0) + 1


# Backward-compat alias (old private name used across the pipeline).
_bump_run_stat = bump_run_stat


def source_distribution(items: List[NewsItem]) -> Dict[str, int]:
    """Count selected candidates by source for run-level observability."""
    counts: Dict[str, int] = {}
    for item in items:
        source = (item.source or "unknown").strip() or "unknown"
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower())))


# Backward-compat alias.
_source_distribution = source_distribution


def build_summary(
    *,
    started_at: str,
    finished_at: str,
    candidates: int,
    active_topic_ids: List[str],
    new_posts_saved: int,
    run_stats: Dict[str, int],
    budget_stopped_early: bool = False,
    batch_insert_ok: Optional[bool] = None,
    selected_items: Optional[List[NewsItem]] = None,
    note: Optional[str] = None,
) -> Dict:
    """Build the JSON-serializable pipeline_summary payload."""
    summary: Dict = {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": finished_at,
        "candidates": candidates,
        "active_topic_ids": active_topic_ids,
        "new_posts_saved": new_posts_saved,
        "budget_stopped_early": budget_stopped_early,
        "batch_insert_ok": batch_insert_ok,
        "estimated_cost_usd": round(cost_tracker.get_current_cost(), 6),
        "skipped_invalid_url": run_stats.get("skipped_invalid_url", 0),
        "skipped_duplicate_url": run_stats.get("skipped_duplicate_url", 0),
        "generated_ok": run_stats.get("generated_ok", 0),
        "failed_ai": run_stats.get("failed_ai", 0),
        "failed_validation": run_stats.get("failed_validation", 0),
        "processing_errors": run_stats.get("processing_errors", 0),
    }
    if selected_items is not None:
        summary["selected_by_source"] = source_distribution(selected_items)
    if note is not None:
        summary["note"] = note
    return summary


def log_summary(summary: Dict) -> None:
    """Emit the pipeline summary as a single JSON log line."""
    from infra.logger import get_logger

    get_logger("ingest").info("pipeline_summary %s", json.dumps(summary))
