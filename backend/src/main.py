import json
import os
import re
import sys
import time
from datetime import datetime
from typing import List, Set, Optional, Dict
from urllib.parse import urlparse
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase_client, get_all_existing_urls
from ingest import get_latest_news, NewsItem
from scraper import scrape_article
from generator import generate_blog_post
from ai_audit import log_ai_generation_result
from logger import get_logger
from security import sanitize_text, validate_url, validate_ai_output, MAX_TITLE_LENGTH
from metrics import cost_tracker

logger = get_logger("ingest")

_AGGREGATOR_SOURCES = {"hacker news", "hacker news best"}
_PUBLISHER_NAME_MAP = {
    "github": "GitHub",
    "bsky": "Bluesky",
    "nytimes": "The New York Times",
    "wsj": "The Wall Street Journal",
}


def validate_environment() -> bool:
    """Validate all required environment variables at startup."""
    if not os.getenv("SUPABASE_URL"):
        logger.error("Missing required environment variables: SUPABASE_URL")
        return False
    
    has_supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not has_supabase_key:
        logger.error("Missing required environment variables: SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY")
        return False
    
    has_any_ai_key = os.getenv("GOOGLE_API_KEY") or os.getenv("OPEN_ROUTER_API_KEY")
    if not has_any_ai_key:
        logger.error("No AI API keys found (GOOGLE_API_KEY or OPEN_ROUTER_API_KEY required)")
        return False
    
    return True


def _publisher_name_from_url(url: str) -> str:
    """Derive a human-friendly publisher name from an article URL."""
    if not url:
        return ""
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return ""
    host = re.sub(r"^(www\.|m\.)", "", host)
    if not host:
        return ""

    parts = [p for p in host.split(".") if p]
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "net"}:
        base = parts[-3]
    elif len(parts) >= 2:
        base = parts[-2]
    else:
        base = parts[0]

    if base in _PUBLISHER_NAME_MAP:
        return _PUBLISHER_NAME_MAP[base]

    return re.sub(r"[-_]+", " ", base).strip().title()


def resolve_display_source_name(feed_source: str, article_url: str) -> str:
    """Prefer original publisher for aggregator feeds (e.g. Hacker News)."""
    source = (feed_source or "").strip()
    if source.lower() in _AGGREGATOR_SOURCES:
        publisher = _publisher_name_from_url(article_url)
        if publisher:
            return publisher
    return source


def format_context_for_ai(item: NewsItem, article_content: str = "", source_name: Optional[str] = None) -> str:
    """Format news item and article content for AI context."""
    sanitized_title = sanitize_text(item.title, MAX_TITLE_LENGTH)
    sanitized_link = item.link if validate_url(item.link) else ""
    sanitized_source = sanitize_text(source_name or item.source, 50)
    
    context = f"""Source: {sanitized_source}
Title: {sanitized_title}
Link: {sanitized_link}
Date: {item.pub_date.isoformat()}
"""
    if article_content:
        sanitized_content = sanitize_text(article_content, 4000)
        context += f"\nArticle Content:\n{sanitized_content}"
    else:
        sanitized_snippet = sanitize_text(item.snippet, 1000)
        context += f"\nSnippet: {sanitized_snippet}"
    
    return context


def save_post(client, post_data: dict) -> bool:
    """Save generated post to database."""
    try:
        tag_ids = []
        
        if post_data.get("tags"):
            for tag_name in post_data["tags"]:
                slug = tag_name.lower().replace(" ", "-")
                slug = re.sub(r'[^a-z0-9-]', '', slug)
                slug = re.sub(r'-+', '-', slug).strip('-')
                
                tag_response = client.from_("tags").upsert(
                    {"name": tag_name, "slug": slug},
                    on_conflict="slug"
                ).execute()
                
                if tag_response.data:
                    tag_ids.append(tag_response.data[0]["id"])
                else:
                    existing = client.from_("tags").select("id").eq("slug", slug).execute()
                    if existing.data:
                        tag_ids.append(existing.data[0]["id"])
        
        post_response = client.from_("posts").insert({
            "title": post_data["title"],
            "slug": post_data["slug"],
            "content": post_data.get("content", ""),
            "excerpt": post_data.get("excerpt", ""),
            "tldr": post_data.get("tldr", []),
            "source_url": post_data.get("source_url", []),
            "ai_model": post_data.get("ai_model", "gemini-2.5-pro"),
            "is_published": True,
            "published_at": datetime.now().isoformat(),
            "cover_image": post_data.get("cover_image", "https://images.unsplash.com/photo-1677442136019-21780ecad995")
        }).execute()
        
        if not post_response.data:
            logger.error("Failed to insert post")
            return False
        
        post_id = post_response.data[0]["id"]
        
        if tag_ids:
            post_tags = [{"post_id": post_id, "tag_id": tid} for tid in tag_ids]
            client.from_("post_tags").insert(post_tags).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving post: {e}")
        return False


def _bump_run_stat(run_stats: Optional[Dict[str, int]], key: str) -> None:
    if run_stats is not None:
        run_stats[key] = run_stats.get(key, 0) + 1


def _source_distribution(items: List[NewsItem]) -> Dict[str, int]:
    """Count selected candidates by source for run-level observability."""
    counts: Dict[str, int] = {}
    for item in items:
        source = (item.source or "unknown").strip() or "unknown"
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower())))


def process_news_item(
    client,
    item: NewsItem,
    existing_urls: set,
    max_retries: int = 2,
    run_stats: Optional[Dict[str, int]] = None,
) -> bool:
    """Process a single news item: check duplicate, scrape, generate, save."""
    if not validate_url(item.link):
        logger.warning(f"  Invalid URL, skipping: {item.link}")
        _bump_run_stat(run_stats, "skipped_invalid_url")
        return False
    
    if item.link in existing_urls:
        logger.info(f"  Skipping duplicate: {item.link}")
        _bump_run_stat(run_stats, "skipped_duplicate_url")
        return False
    
    logger.info(f"  Processing: {item.title[:50]}...")
    
    for attempt in range(max_retries):
        try:
            display_source_name = resolve_display_source_name(item.source, item.link)
            logger.debug(f"    Scraping article content...")
            article_content = scrape_article(item.link)
            
            context = format_context_for_ai(item, article_content, source_name=display_source_name)
            
            logger.debug(f"    Generating blog post...")
            post_data = generate_blog_post(
                topic=item.title,
                article_content=context,
                source_name=display_source_name,
                source_url=item.link
            )
            
            if not post_data:
                if attempt < max_retries - 1:
                    logger.warning(f"    AI failed, retrying...")
                    time.sleep(5)
                    continue
                logger.error("    AI generation failed after all retries, skipping")
                _bump_run_stat(run_stats, "failed_ai")
                log_ai_generation_result(
                    client=client,
                    topic=item.title,
                    source_name=display_source_name,
                    source_url=item.link,
                    status="failed",
                    failure_reason="ai_generation_failed",
                    validated=False,
                )
                return False
            
            validation_error = validate_ai_output(post_data)
            if validation_error:
                logger.error(f"    AI output validation failed: {validation_error}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                logger.error("    AI output invalid after all retries, skipping")
                _bump_run_stat(run_stats, "failed_validation")
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
                return False
            
            log_ai_generation_result(
                client=client,
                topic=item.title,
                source_name=display_source_name,
                source_url=item.link,
                status="generated",
                output_json=post_data,
                validated=True,
            )
            _bump_run_stat(run_stats, "generated_ok")
            logger.debug(f"    Saving to database...")
            success = save_post(client, post_data)
            
            if success:
                logger.info(f"    ✓ Saved: {post_data['title'][:40]}")
                return True
            else:
                if attempt < max_retries - 1:
                    logger.warning(f"    Save failed, retrying...")
                    time.sleep(3)
                    continue
                logger.error(f"    ✗ Failed to save")
                return False
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"    Error (attempt {attempt + 1}): {e}, retrying...")
                time.sleep(5)
                continue
            logger.error(f"    ✗ Error processing after {max_retries} attempts: {e}")
            _bump_run_stat(run_stats, "processing_errors")
            return False
    
    return False


def process_news_item_for_batch(
    client,
    item: NewsItem,
    existing_urls: set,
    max_retries: int = 2,
    run_stats: Optional[Dict[str, int]] = None,
) -> Optional[Dict]:
    """Process a single news item and return post data for batch saving."""
    if not validate_url(item.link):
        logger.warning(f"  Invalid URL, skipping: {item.link}")
        _bump_run_stat(run_stats, "skipped_invalid_url")
        return None
    
    if item.link in existing_urls:
        logger.info(f"  Skipping duplicate: {item.link}")
        _bump_run_stat(run_stats, "skipped_duplicate_url")
        return None
    
    logger.info(f"  Processing: {item.title[:50]}...")
    
    for attempt in range(max_retries):
        try:
            display_source_name = resolve_display_source_name(item.source, item.link)
            logger.debug(f"    Scraping article content...")
            article_content = scrape_article(item.link)
            
            context = format_context_for_ai(item, article_content, source_name=display_source_name)
            
            logger.debug(f"    Generating blog post...")
            post_data = generate_blog_post(
                topic=item.title,
                article_content=context,
                source_name=display_source_name,
                source_url=item.link
            )
            
            if not post_data:
                if attempt < max_retries - 1:
                    logger.warning(f"    AI failed, retrying...")
                    time.sleep(5)
                    continue
                logger.error("    AI generation failed after all retries, skipping")
                _bump_run_stat(run_stats, "failed_ai")
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
            
            validation_error = validate_ai_output(post_data)
            if validation_error:
                logger.error(f"    AI output validation failed: {validation_error}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                logger.error("    AI output invalid after all retries, skipping")
                _bump_run_stat(run_stats, "failed_validation")
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
            _bump_run_stat(run_stats, "generated_ok")
            logger.info(f"    ✓ Generated: {post_data['title'][:40]}")
            return post_data
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"    Error (attempt {attempt + 1}): {e}, retrying...")
                time.sleep(5)
                continue
            logger.error(f"    ✗ Error processing after {max_retries} attempts: {e}")
            _bump_run_stat(run_stats, "processing_errors")
            return None
    
    return None


def batch_save_posts(client, posts_data: List[Dict]) -> bool:
    """Save multiple posts in a single batch transaction."""
    try:
        tag_map = {}
        all_tags = set()
        
        for post_data in posts_data:
            if post_data.get("tags"):
                for tag_name in post_data["tags"]:
                    slug = tag_name.lower().replace(" ", "-")
                    slug = re.sub(r'[^a-z0-9-]', '', slug)
                    slug = re.sub(r'-+', '-', slug).strip('-')
                    all_tags.add((tag_name, slug))
        
        if all_tags:
            for tag_name, slug in all_tags:
                tag_response = client.from_("tags").upsert(
                    {"name": tag_name, "slug": slug},
                    on_conflict="slug"
                ).execute()
                if tag_response.data:
                    tag_map[slug] = tag_response.data[0]["id"]
            
            for tag_name, slug in all_tags:
                if slug not in tag_map:
                    existing = client.from_("tags").select("id").eq("slug", slug).execute()
                    if existing.data:
                        tag_map[slug] = existing.data[0]["id"]
        
        posts_to_insert = []
        post_tags_list = []
        for post_data in posts_data:
            post_tags = []
            if post_data.get("tags"):
                for tag_name in post_data["tags"]:
                    slug = tag_name.lower().replace(" ", "-")
                    slug = re.sub(r'[^a-z0-9-]', '', slug)
                    if slug in tag_map:
                        post_tags.append(tag_map[slug])
            
            post_data_clean = {
                "title": post_data["title"],
                "slug": post_data["slug"],
                "content": post_data.get("content", ""),
                "excerpt": post_data.get("excerpt", ""),
                "tldr": post_data.get("tldr", []),
                "source_url": post_data.get("source_url", []),
                "ai_model": post_data.get("ai_model", "gemini-2.5-flash"),
                "is_published": True,
                "published_at": datetime.now().isoformat(),
                "cover_image": post_data.get("cover_image", "https://images.unsplash.com/photo-1677442136019-21780ecad995")
            }
            posts_to_insert.append(post_data_clean)
            post_tags_list.append(post_tags)
        
        response = client.from_("posts").insert(posts_to_insert).execute()
        
        if not response.data:
            logger.error("Batch insert failed - no data returned")
            return False
        
        post_tags_to_insert = []
        for i, post in enumerate(response.data):
            post_id = post["id"]
            tag_ids = post_tags_list[i] if i < len(post_tags_list) else []
            for tag_id in tag_ids:
                post_tags_to_insert.append({"post_id": post_id, "tag_id": tag_id})
        
        if post_tags_to_insert:
            client.from_("post_tags").insert(post_tags_to_insert).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Batch save error: {e}")
        return False


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
    
    logger.info("[2/4] Fetching latest tech news...")
    news_items = get_latest_news(limit=5)
    logger.info(f"    Found {len(news_items)} candidate items")
    
    if not news_items:
        logger.warning("    No news found. Exiting.")
        logger.info(
            "pipeline_summary %s",
            json.dumps(
                {
                    "schema_version": 1,
                    "started_at": started_at,
                    "finished_at": datetime.now().isoformat(),
                    "candidates": 0,
                    "new_posts_saved": 0,
                    "note": "no_feed_matches",
                }
            ),
        )
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
                client, item, existing_urls, run_stats=run_stats
            )
            if post_data:
                pending_posts.append(post_data)
                time.sleep(2)
        except Exception as e:
            logger.error(f"    Error processing {item.title}: {e}")
            _bump_run_stat(run_stats, "processing_errors")
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
    summary = {
        "schema_version": 1,
        "started_at": started_at,
        "finished_at": finished_at,
        "candidates": len(news_items),
        "selected_by_source": _source_distribution(news_items),
        "new_posts_saved": success_count,
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
    logger.info("pipeline_summary %s", json.dumps(summary))
    
    logger.info("=" * 60)
    logger.info("Pipeline Complete!")
    logger.info(f"  Candidates: {len(news_items)} items")
    logger.info(f"  New posts: {success_count}")
    logger.info(f"  Skipped (see pipeline_summary): duplicates / invalid URL / AI / validation")
    logger.info(f"Finished at: {finished_at}")
    logger.info("=" * 60)
    
    cost_tracker.log_summary()


if __name__ == "__main__":
    main()