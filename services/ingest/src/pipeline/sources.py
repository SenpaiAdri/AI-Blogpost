"""Aggregator-aware source attribution (e.g. Hacker News -> original publisher)."""

import re
from urllib.parse import urlparse

_AGGREGATOR_SOURCES = {"hacker news", "hacker news best"}
_PUBLISHER_NAME_MAP = {
    "github": "GitHub",
    "bsky": "Bluesky",
    "nytimes": "The New York Times",
    "wsj": "The Wall Street Journal",
}


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
