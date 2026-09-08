"""Top-level pipeline run: connect -> fetch -> dedupe -> process -> batch save."""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

from infra.ai_audit import log_ai_generation_result  # noqa: F401 (public pipeline API)
from infra.database import (
    get_active_rss_sources,
    get_active_topic_guidance,
    get_all_existing_urls,
    get_supabase_client,
)
from infra.logger import get_logger
from infra.metrics import cost_tracker
from pipeline.persistence import batch_save_posts, save_post  # noqa: F401
from pipeline.processor import process_news_item, process_news_item_for_batch  # noqa: F401
from pipeline.run_stats import build_summary, log_summary
from selection.feeds import get_latest_news

logger = get_logger("ingest")


def validate_environment() -> bool:
    """Validate all required environment variables at startup."""
    if not os.getenv("SUPABASE_URL"):
        logger.error("Missing required environment variables: SUPABASE_URL")
        return False

    has_supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not has_supabase_key:
        logger.error("Missing required environment variables: SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY")
        return False

    if not os.getenv("OPEN_ROUTER_API_KEY"):
        logger.error("Missing required environment variables: OPEN_ROUTER_API_KEY")
        return False

    return True


def main():
    """Main ingestion pipeline."""
    if not validate_environment():
        logger.error("Environment validation failed. Exiting.")
        sys.exit(1)

    started_at = datetime.now().isoformat()
    run_stats: Dict[str, int] = {}

    logger.info("=" * 60)
    logger.info("AI Blog Post Ingestion Pipeline")
    logger.info(f"Started at: {started_at}")
    logger.info("=" * 60)

    logger.info("[1/4] Connecting to Supabase...")
    client = get_supabase_client()
    logger.info("    Connected")

    active_topics = get_active_topic_guidance(client)
    active_topic_ids = [str(topic.get("id")) for topic in active_topics if topic.get("id")]
    if active_topics:
        logger.info(f"    Active topic guidance: {len(active_topics)} topic(s)")
    else:
        logger.info("    Active topic guidance: none")

    active_rss_sources = get_active_rss_sources(client)
    if active_rss_sources:
        logger.info(f"    Active RSS sources: {len(active_rss_sources)} feed(s) from DB")
    else:
        logger.info("    Active RSS sources: using hardcoded defaults")

    logger.info("[2/4] Fetching latest tech news...")
    news_items = get_latest_news(limit=5, active_topics=active_topics, rss_feeds=active_rss_sources)
    logger.info(f"    Found {len(news_items)} candidate items")

    if not news_items:
        logger.warning("    No news found. Exiting.")
        log_summary(build_summary(
            started_at=started_at,
            finished_at=datetime.now().isoformat(),
            candidates=0,
            active_topic_ids=active_topic_ids,
            new_posts_saved=0,
            run_stats=run_stats,
            note="no_feed_matches",
        ))
        return

    for i, item in enumerate(news_items, 1):
        logger.info(f"    {i}. [{item.source}] {item.title[:40]}...")

    logger.info("[3/4] Checking for duplicates...")
    existing_urls = get_all_existing_urls(client)
    logger.info(f"    Found {len(existing_urls)} existing URLs in database")

    logger.info("[4/4] Processing news items...")
    pending_posts = []
    budget_stopped_early = False

    for item in news_items:
        if not cost_tracker.should_continue():
            logger.warning("Budget exhausted, stopping early")
            budget_stopped_early = True
            break

        try:
            post_data = process_news_item_for_batch(
                client, item, existing_urls, run_stats=run_stats, active_topics=active_topics
            )
            if post_data:
                pending_posts.append(post_data)
                time.sleep(2)
        except Exception as e:
            logger.error(f"    Error processing {item.title}: {e}")
            from pipeline.run_stats import bump_run_stat

            bump_run_stat(run_stats, "processing_errors")
            continue

    success_count = 0
    batch_insert_ok: Optional[bool] = None
    if pending_posts:
        logger.info(f"    Inserting {len(pending_posts)} posts in batch...")
        batch_success = batch_save_posts(client, pending_posts)
        batch_insert_ok = batch_success
        if batch_success:
            success_count = len(pending_posts)
            logger.info(f"    ✓ Batch inserted {success_count} posts")
        else:
            logger.warning("    Batch insert failed, posts were not saved")

    finished_at = datetime.now().isoformat()
    summary = build_summary(
        started_at=started_at,
        finished_at=finished_at,
        candidates=len(news_items),
        active_topic_ids=active_topic_ids,
        new_posts_saved=success_count,
        run_stats=run_stats,
        budget_stopped_early=budget_stopped_early,
        batch_insert_ok=batch_insert_ok,
        selected_items=news_items,
    )
    log_summary(summary)

    logger.info("=" * 60)
    logger.info("Pipeline Complete!")
    logger.info(f"  Candidates: {len(news_items)} items")
    logger.info(f"  New posts: {success_count}")
    logger.info("  Skipped (see pipeline_summary): duplicates / invalid URL / AI / validation")
    logger.info(f"Finished at: {finished_at}")
    logger.info("=" * 60)

    cost_tracker.log_summary()


if __name__ == "__main__":
    main()
