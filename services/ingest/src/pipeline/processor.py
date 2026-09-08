"""Per-item processing: dedupe gate -> scrape -> generate -> validate -> audit.

The two public entry points share one core helper so retry / validation /
audit behavior cannot drift between the inline-save and batch-save paths:

- :func:`process_news_item` — generates AND saves inline, returns bool.
- :func:`process_news_item_for_batch` — generates, returns post dict for
  deferred batch insert.
"""

import time
from typing import Dict, List, Optional

from generation.llm_client import generate_blog_post
from infra.ai_audit import log_ai_generation_result
from infra.logger import get_logger
from models import PostInsertModel
from pipeline.formatting import format_context_for_ai
from pipeline.persistence import save_post
from pipeline.run_stats import bump_run_stat
from pipeline.sources import resolve_display_source_name
from pydantic import ValidationError
from safety.url_validation import validate_url
from selection.models import NewsItem
from selection.scraper import scrape_article
from selection.topics import matched_topic_ids

logger = get_logger("ingest")


def _generate_validated_post(
    client,
    item: NewsItem,
    display_source_name: str,
    active_topics: Optional[List[Dict]],
    max_retries: int,
    run_stats: Optional[Dict[str, int]],
) -> Optional[Dict]:
    """Scrape -> generate -> Pydantic-validate with retries. Returns post dict or None."""
    for attempt in range(max_retries):
        try:
            matched_topics = matched_topic_ids(item, active_topics)
            if matched_topics:
                logger.info(f"    Matched topic guidance: {', '.join(matched_topics)}")
            logger.debug("    Scraping article content...")
            article_content = scrape_article(item.link)

            context = format_context_for_ai(item, article_content, source_name=display_source_name)

            logger.debug("    Generating blog post...")
            post_data = generate_blog_post(
                topic=item.title,
                article_content=context,
                source_name=display_source_name,
                source_url=item.link,
                active_topics=active_topics,
            )

            if not post_data:
                if attempt < max_retries - 1:
                    logger.warning("    AI failed, retrying...")
                    time.sleep(5)
                    continue
                logger.error("    AI generation failed after all retries, skipping")
                bump_run_stat(run_stats, "failed_ai")
                log_ai_generation_result(
                    client=client,
                    topic=item.title,
                    source_name=display_source_name,
                    source_url=item.link,
                    status="failed",
                    failure_reason="ai_generation_failed",
                    validated=False,
                )
                return None

            try:
                validated_post = PostInsertModel(**post_data)
                post_data = validated_post.model_dump(mode='json')
            except ValidationError as e:
                validation_error = str(e).replace('\n', ' | ')
                logger.error(f"    AI output validation failed: {validation_error}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                logger.error("    AI output invalid after all retries, skipping")
                bump_run_stat(run_stats, "failed_validation")
                log_ai_generation_result(
                    client=client,
                    topic=item.title,
                    source_name=display_source_name,
                    source_url=item.link,
                    status="failed",
                    output_json=post_data,
                    failure_reason=f"validation_failed: {validation_error}",
                    validated=False,
                )
                return None

            log_ai_generation_result(
                client=client,
                topic=item.title,
                source_name=display_source_name,
                source_url=item.link,
                status="generated",
                output_json=post_data,
                validated=True,
            )
            bump_run_stat(run_stats, "generated_ok")
            return post_data

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"    Error (attempt {attempt + 1}): {e}, retrying...")
                time.sleep(5)
                continue
            logger.error(f"    ✗ Error processing after {max_retries} attempts: {e}")
            bump_run_stat(run_stats, "processing_errors")
            return None

    return None


def _check_processable(
    item: NewsItem,
    existing_urls: set,
    run_stats: Optional[Dict[str, int]],
) -> Optional[str]:
    """URL + duplicate gates. Returns display source name, or None to skip."""
    if not validate_url(item.link):
        logger.warning(f"  Invalid URL, skipping: {item.link}")
        bump_run_stat(run_stats, "skipped_invalid_url")
        return None

    if item.link in existing_urls:
        logger.info(f"  Skipping duplicate: {item.link}")
        bump_run_stat(run_stats, "skipped_duplicate_url")
        return None

    logger.info(f"  Processing: {item.title[:50]}...")
    return resolve_display_source_name(item.source, item.link)


def process_news_item(
    client,
    item: NewsItem,
    existing_urls: set,
    max_retries: int = 2,
    run_stats: Optional[Dict[str, int]] = None,
    active_topics: Optional[List[Dict]] = None,
) -> bool:
    """Process a single news item: check duplicate, scrape, generate, save."""
    display_source_name = _check_processable(item, existing_urls, run_stats)
    if display_source_name is None:
        return False

    post_data = _generate_validated_post(
        client, item, display_source_name, active_topics,
        max_retries=max_retries, run_stats=run_stats,
    )
    if post_data is None:
        return False

    for attempt in range(max_retries):
        logger.debug("    Saving to database...")
        if save_post(client, post_data):
            logger.info(f"    ✓ Saved: {post_data['title'][:40]}")
            return True
        if attempt < max_retries - 1:
            logger.warning("    Save failed, retrying...")
            time.sleep(3)
            continue
        logger.error("    ✗ Failed to save")
        return False

    return False


def process_news_item_for_batch(
    client,
    item: NewsItem,
    existing_urls: set,
    max_retries: int = 2,
    run_stats: Optional[Dict[str, int]] = None,
    active_topics: Optional[List[Dict]] = None,
) -> Optional[Dict]:
    """Process a single news item and return post data for batch saving."""
    display_source_name = _check_processable(item, existing_urls, run_stats)
    if display_source_name is None:
        return None

    post_data = _generate_validated_post(
        client, item, display_source_name, active_topics,
        max_retries=max_retries, run_stats=run_stats,
    )
    if post_data:
        logger.info(f"    ✓ Generated: {post_data['title'][:40]}")
    return post_data
