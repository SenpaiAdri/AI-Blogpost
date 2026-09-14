"""Scheduled entrypoint: score recent posts, comment selectively.

Run: python services/ingest/src/comments/runner.py  (repo root)
Mirrors pipeline/orchestrator.py env validation; Supabase is the only
integration boundary (never calls the web app).
"""

import os
import sys
import time
from pathlib import Path

# Allow `python src/comments/runner.py`: put src/ on sys.path like main.py gets.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

from comments.generator import (
    InsufficientCredits,
    generate_comment_for_post,
    score_post,
)
from comments.persistence import save_comment
from config import (
    COMMENTS_DRY_RUN,
    COMMENTS_LOOKBACK_HOURS,
    COMMENTS_MAX_COMMENTS,
    COMMENTS_MAX_CONSECUTIVE_ERRORS,
    COMMENTS_MAX_POSTS,
    COMMENTS_THRESHOLD,
)
from infra.ai_audit import log_ai_generation_result
from infra.database import (
    get_approved_ai_commented_post_ids,
    get_recent_posts,
    get_supabase_client,
    has_approved_ai_comment,
)
from infra.logger import get_logger
from infra.metrics import cost_tracker

logger = get_logger("comments")


def _audit_source(post: dict) -> tuple:
    """(topic, source_url) identifiers for ai_generation_logs rows."""
    topic = str(post.get("title") or post.get("slug") or post.get("id") or "unknown")
    return topic, f"post:{post.get('slug') or post.get('id')}"


def process_post(client, post: dict, commented_ids=None) -> str:
    """Score + maybe comment on one post.

    commented_ids: pre-fetched set from get_approved_ai_commented_post_ids
    (None = unknown, fall back to a per-post check).

    Returns one of: 'commented', 'skipped_exists', 'skipped_score',
    'failed_check', 'failed_score', 'failed_generate', 'failed_save'.
    """
    post_id = str(post.get("id"))
    topic, source_url = _audit_source(post)

    if commented_ids is not None:
        if post_id in commented_ids:
            return "skipped_exists"
    else:
        try:
            if has_approved_ai_comment(client, post_id):
                return "skipped_exists"
        except Exception as e:
            logger.warning(f"Comment check failed for post {post_id}: {e}")
            return "failed_check"

    score, reason, score_model = score_post(post)
    if score_model is None:
        log_ai_generation_result(
            client, topic, "ai-comment", source_url,
            status="comment_scoring_failed",
            output_json={"score": score, "reason": reason},
            failure_reason=reason[:2000] if reason else "scoring_failed",
        )
        return "failed_score"

    if score < COMMENTS_THRESHOLD:
        logger.info(f"    Score {score:.1f} < {COMMENTS_THRESHOLD} ({reason}); skipping")
        log_ai_generation_result(
            client, topic, "ai-comment", source_url,
            status="comment_filtered_by_threshold",
            output_json={"score": score, "reason": reason, "ai_model": score_model},
        )
        return "skipped_score"

    result = generate_comment_for_post(post)
    if not result:
        log_ai_generation_result(
            client, topic, "ai-comment", source_url,
            status="comment_generation_failed",
            output_json={"score": score, "reason": reason, "ai_model": score_model},
            failure_reason="comment_generation_failed",
        )
        return "failed_generate"

    audit_status = "comment_dry_run" if COMMENTS_DRY_RUN else "comment_generated"
    log_ai_generation_result(
        client, topic, "ai-comment", source_url,
        status=audit_status,
        output_json={
            "comment": result["body"],
            "score": score,
            "reason": reason,
            "ai_model": result["ai_model"],
        },
        validated=True,
    )

    ok = save_comment(
        client, post_id, result["body"], ai_model=result["ai_model"],
        dry_run=COMMENTS_DRY_RUN,
    )
    return "commented" if ok else "failed_save"


def run_loop(client, posts: list) -> dict:
    """Score/comment loop with a consecutive-error circuit breaker.

    Stops early on: comment cap, our budget gate, exhausted OpenRouter
    credits (402: same key funds both models, so retrying cannot help),
    or COMMENTS_MAX_CONSECUTIVE_ERRORS provider/DB failures in a row
    (429 storms, persistent empties). Returns per-outcome stats.
    """
    try:
        commented_ids: set | None = get_approved_ai_commented_post_ids(
            client, [p.get("id") for p in posts]
        )
    except Exception as e:
        logger.warning(f"Batch comment check failed, falling back per post: {e}")
        commented_ids = None

    stats: dict = {}
    commented = 0
    consec_errors = 0
    for i, post in enumerate(posts):
        if commented >= COMMENTS_MAX_COMMENTS:
            break
        if not cost_tracker.should_continue():
            logger.warning("Budget exhausted, stopping comment run")
            break
        try:
            outcome = process_post(client, post, commented_ids)
        except InsufficientCredits as e:
            # Print the provider's reason: key monthly limit vs empty
            # balance need opposite fixes (raise cap vs buy credits).
            logger.warning(f"OpenRouter credits/key limit hit; stopping comment run: {e}")
            stats["failed_credits"] = stats.get("failed_credits", 0) + 1
            break
        stats[outcome] = stats.get(outcome, 0) + 1
        if outcome == "commented":
            commented += 1
            consec_errors = 0
        elif outcome in ("failed_check", "failed_score", "failed_generate"):
            consec_errors += 1
            if consec_errors >= COMMENTS_MAX_CONSECUTIVE_ERRORS:
                logger.warning(
                    f"{consec_errors} consecutive errors; stopping comment run"
                )
                break
        else:
            consec_errors = 0  # skips prove the provider is answering
        if i < len(posts) - 1:
            time.sleep(2)
    return stats


def main() -> None:
    if not os.getenv("SUPABASE_URL") or not (
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    ):
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)
    if not os.getenv("OPEN_ROUTER_API_KEY"):
        logger.error("Missing OPEN_ROUTER_API_KEY")
        sys.exit(1)

    client = get_supabase_client()
    posts = get_recent_posts(client, COMMENTS_LOOKBACK_HOURS, COMMENTS_MAX_POSTS)
    logger.info(f"Scoring {len(posts)} recent posts (max {COMMENTS_MAX_COMMENTS} comments)")

    stats = run_loop(client, posts)

    logger.info(f"Comment run done: {stats}")
    cost_tracker.log_summary()


if __name__ == "__main__":
    main()
