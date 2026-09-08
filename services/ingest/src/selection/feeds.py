"""RSS fetching + selection orchestration: fetch -> filter -> prioritize -> diversify."""

import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

from config import FETCH_ITEMS_PER_FEED, MAX_FEED_WORKERS, MAX_PER_SOURCE
from infra.logger import get_logger
from infra.rate_limit import wait_for_url
from selection.dedupe import dedupe_news_items
from selection.models import NewsItem
from selection.relevance import filter_tech_news
from selection.rss_feeds import RSS_FEEDS
from selection.topics import prioritize_news_items_by_topics

logger = get_logger("ingest")


def parse_entry_datetime(entry: dict, pub_date_str: str) -> datetime:
    """Parse feed entry timestamps across common RSS/Atom formats."""
    parsed_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_struct:
        try:
            return datetime(*parsed_struct[:6])
        except Exception:
            pass

    raw = (pub_date_str or entry.get("updated", "") or "").strip()
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
        try:
            dt = parsedate_to_datetime(raw)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            pass

    return datetime.now()


def fetch_feed(feed_config: dict) -> List[NewsItem]:
    """Fetch a single RSS feed and return news items."""
    try:
        wait_for_url(feed_config["url"])
        feed = feedparser.parse(feed_config["url"])

        items = []
        for entry in feed.entries[:FETCH_ITEMS_PER_FEED]:
            title = entry.get("title", "No Title")
            link = entry.get("link", "")
            snippet = entry.get("summary", entry.get("description", ""))
            pub_date_str = entry.get("published", "")

            pub_date = parse_entry_datetime(entry, pub_date_str)

            items.append(NewsItem(
                title=title,
                link=link,
                snippet=snippet[:500] if snippet else "",
                source=feed_config["name"],
                pub_date=pub_date
            ))

        return items
    except Exception as e:
        logger.error(f"Error fetching {feed_config['name']}: {e}")
        return []


def fetch_all_news(rss_feeds: Optional[List[Dict]] = None) -> List[NewsItem]:
    """Fetch all RSS feeds in parallel and return combined, sorted news."""
    feeds_to_fetch = rss_feeds if rss_feeds else RSS_FEEDS
    all_news = []
    failed_feeds = []

    with ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
        future_to_feed = {
            executor.submit(fetch_feed, feed_config): feed_config
            for feed_config in feeds_to_fetch
        }

        for future in as_completed(future_to_feed):
            feed_config = future_to_feed[future]
            try:
                items = future.result()
                all_news.extend(items)
                logger.debug(f"Fetched {len(items)} items from {feed_config['name']}")
            except Exception as e:
                logger.warning(f"Failed to fetch {feed_config['name']}: {e}")
                failed_feeds.append(feed_config["name"])

    if failed_feeds:
        logger.warning(f"Failed feeds: {', '.join(failed_feeds)}")

    all_news.sort(key=lambda x: x.pub_date, reverse=True)
    before = len(all_news)
    all_news = dedupe_news_items(all_news)
    dropped = before - len(all_news)
    if dropped:
        logger.debug(f"Deduped {dropped} duplicate story(ies) across feeds")
    return all_news


def diversify_news_items(items: List[NewsItem], limit: int, max_per_source: int = MAX_PER_SOURCE) -> List[NewsItem]:
    """Pick newest items while capping stories per feed source."""
    if limit <= 0 or not items:
        return []

    selected: List[NewsItem] = []
    source_counts: dict[str, int] = {}
    remainder: List[NewsItem] = []

    for item in items:
        src = item.source or "unknown"
        if source_counts.get(src, 0) < max_per_source:
            selected.append(item)
            source_counts[src] = source_counts.get(src, 0) + 1
            if len(selected) >= limit:
                return selected
        else:
            remainder.append(item)

    for item in remainder:
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected[:limit]


def get_latest_news(limit: int = 10, active_topics: Optional[List[Any]] = None, rss_feeds: Optional[List[Dict]] = None) -> List[NewsItem]:
    """Get the latest tech news items (keyword-filtered)."""
    all_news = fetch_all_news(rss_feeds)
    tech_news = filter_tech_news(all_news)
    prioritized = prioritize_news_items_by_topics(tech_news, active_topics)
    diversified = diversify_news_items(prioritized, limit=limit, max_per_source=MAX_PER_SOURCE)
    return diversified


if __name__ == "__main__":
    news = get_latest_news(5)
    for item in news:
        logger.info(f"[{item.source}] {item.title}")
        logger.info(f"   {item.link}")
