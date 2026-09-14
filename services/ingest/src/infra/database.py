import os
import supabase
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from infra.logger import get_logger

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(env_path)

from config import DUPLICATE_CHECK_DAYS

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
logger = get_logger("database")


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    return supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def check_duplicate_url(client, url: str) -> bool:
    """Check if a URL already exists in the database using Supabase JSON containment."""
    response = client.from_("posts").select("id").contains("source_url", [{"url": url}]).execute()
    return len(response.data) > 0


def get_all_existing_urls(client, days: int = None) -> set:
    """Get existing source URLs from the last N days (default from config.py)."""
    if days is None:
        days = DUPLICATE_CHECK_DAYS

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    response = client.from_("posts").select("source_url").gte("published_at", cutoff).execute()
    urls = set()
    for item in response.data:
        if item.get("source_url"):
            for src in item["source_url"]:
                if isinstance(src, dict) and "url" in src:
                    urls.add(src["url"])
    return urls


def get_active_topic_guidance(client) -> list[dict]:
    """Fetch active, non-expired editorial guidance for this ingest run."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        response = (
            client.from_("topic_guidance")
            .select("id,keyword,normalized_keyword,weight,expires_at")
            .eq("status", "ACTIVE")
            .gt("expires_at", now)
            .order("expires_at")
            .execute()
        )
        return response.data or []
    except Exception as exc:
        logger.warning(f"Topic guidance unavailable; continuing without active topics: {exc}")
        return []

def get_active_rss_sources(client) -> list[dict]:
    """Fetch active RSS sources from the database."""
    try:
        response = (
            client.from_("rss_sources")
            .select("name,url")
            .eq("is_active", True)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        logger.warning(f"RSS sources unavailable; continuing with hardcoded feeds: {exc}")
        return []


def get_recent_posts(client, lookback_hours: int = 72, limit: int = 10) -> list[dict]:
    """Fetch recently published posts for AI comment selection (Phase 0 helper)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    response = (
        client.from_("posts")
        .select("id,slug,title,excerpt,content,published_at")
        .eq("is_published", True)
        .gte("published_at", cutoff)
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def has_approved_ai_comment(client, post_id: str) -> bool:
    """Idempotency check: True if post already has an approved AI comment."""
    response = (
        client.from_("comments")
        .select("id")
        .eq("post_id", post_id)
        .eq("author_type", "ai")
        .eq("status", "approved")
        .limit(1)
        .execute()
    )
    return len(response.data or []) > 0


def get_approved_ai_commented_post_ids(client, post_ids: list) -> set:
    """Batch idempotency check: post IDs with an approved AI comment (one query)."""
    ids = [str(pid) for pid in (post_ids or []) if pid]
    if not ids:
        return set()
    response = (
        client.from_("comments")
        .select("post_id")
        .in_("post_id", ids)
        .eq("author_type", "ai")
        .eq("status", "approved")
        .execute()
    )
    return {str(row.get("post_id")) for row in (response.data or []) if row.get("post_id")}
