import os
import supabase
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    return supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def check_duplicate_url(client, url: str) -> bool:
    """Check if a URL already exists in the database."""
    response = client.from_("posts").select("id").eq("source_url", f'{{"url": "{url}"}}').execute()
    return len(response.data) > 0


def get_all_existing_urls(client) -> set:
    """Get all existing source URLs from the database."""
    response = client.from_("posts").select("source_url").execute()
    urls = set()
    for item in response.data:
        if item.get("source_url"):
            for src in item["source_url"]:
                if isinstance(src, dict) and "url" in src:
                    urls.add(src["url"])
    return urls