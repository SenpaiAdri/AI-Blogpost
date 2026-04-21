import os
import supabase
from datetime import datetime, timedelta
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

_DUPLICATE_CHECK_DAYS = 3


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    return supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def check_duplicate_url(client, url: str) -> bool:
    """Check if a URL already exists in the database using Supabase JSON containment."""
    response = client.from_("posts").select("id").contains("source_url", [{"url": url}]).execute()
    return len(response.data) > 0


def get_all_existing_urls(client, days: int = None) -> set:
    """Get existing source URLs from the last N days (default 3)."""
    if days is None:
        days = _DUPLICATE_CHECK_DAYS
    
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    response = client.from_("posts").select("source_url").gte("published_at", cutoff).execute()
    urls = set()
    for item in response.data:
        if item.get("source_url"):
            for src in item["source_url"]:
                if isinstance(src, dict) and "url" in src:
                    urls.add(src["url"])
    return urls