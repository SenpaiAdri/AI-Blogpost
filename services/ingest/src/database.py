import os
import supabase
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from logger import get_logger

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
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
