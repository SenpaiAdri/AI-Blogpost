import feedparser
from dataclasses import dataclass
from typing import List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from logger import get_logger
from rate_limit import wait_for_url

logger = get_logger("ingest")

_thread_local = threading.local()


@dataclass
class NewsItem:
    title: str
    link: str
    snippet: str
    source: str
    pub_date: datetime


RSS_FEEDS = [
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "Hacker News Best", "url": "https://hnrss.org/best"},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "DeepMind Blog", "url": "https://deepmind.google/rss/"},
    {"name": "Anthropic", "url": "https://www.anthropic.com/rss.xml"},
    {"name": "AI News", "url": "https://news.ycombinator.com/rss"},
]

AI_KEYWORDS = [
    "ai", "artificial intelligence", "gpt", "llm", "neural", 
    "robot", "machine learning", "nvidia", "gemini", "claude", 
    "openai", "anthropic", "deepmind", "google ai", "chatgpt",
    "large language model", "llama", "gemma", "mistral", "stable diffusion"
]


def fetch_feed(feed_config: dict) -> List[NewsItem]:
    """Fetch a single RSS feed and return news items."""
    try:
        wait_for_url(feed_config["url"])
        feed = feedparser.parse(feed_config["url"])
        
        items = []
        for entry in feed.entries[:15]:
            title = entry.get("title", "No Title")
            link = entry.get("link", "")
            snippet = entry.get("summary", entry.get("description", ""))
            pub_date_str = entry.get("published", "")
            
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                pub_date = pub_date.replace(tzinfo=None)
            except:
                pub_date = datetime.now()
            
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


def fetch_all_news() -> List[NewsItem]:
    """Fetch all RSS feeds in parallel and return combined, sorted news."""
    all_news = []
    failed_feeds = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_feed = {
            executor.submit(fetch_feed, feed_config): feed_config 
            for feed_config in RSS_FEEDS
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
    return all_news


def filter_ai_news(news_items: List[NewsItem]) -> List[NewsItem]:
    """Filter news items for AI-related content."""
    filtered = []
    
    for item in news_items:
        text = (item.title + " " + item.snippet).lower()
        if any(keyword in text for keyword in AI_KEYWORDS):
            filtered.append(item)
    
    return filtered


def get_latest_news(limit: int = 10) -> List[NewsItem]:
    """Get the latest AI news items."""
    all_news = fetch_all_news()
    ai_news = filter_ai_news(all_news)
    return ai_news[:limit]


if __name__ == "__main__":
    news = get_latest_news(5)
    for item in news:
        logger.info(f"[{item.source}] {item.title}")
        logger.info(f"   {item.link}")