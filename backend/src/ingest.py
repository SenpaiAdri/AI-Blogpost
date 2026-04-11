import difflib
import feedparser
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from logger import get_logger
from rate_limit import wait_for_url
from rss_feeds import RSS_FEEDS

logger = get_logger("ingest")

_thread_local = threading.local()


@dataclass
class NewsItem:
    title: str
    link: str
    snippet: str
    source: str
    pub_date: datetime


# Title/snippet must match at least one keyword using word boundaries (see _TECH_KEYWORD_PATTERNS).
# Avoid very short ambiguous tokens (e.g. "it", "go").
TECH_KEYWORDS = [
    # AI / ML
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "gpt", "llm", "neural", "chatgpt", "openai", "anthropic", "deepmind",
    "gemini", "claude", "llama", "gemma", "mistral", "nvidia", "stable diffusion",
    "large language model", "generative",
    # Security / IT operations
    "security", "cybersecurity", "ransomware", "vulnerability", "breach", "malware",
    "patch", "encryption", "privacy", "phishing", "zero-day", "zeroday",
    # Cloud / infrastructure / DevOps
    "cloud", "kubernetes", "docker", "devops", "aws", "azure", "gcp",
    "server", "datacenter", "data center", "infrastructure",
    # Software / development
    "developer", "programming", "software", "open source", "github",
    "linux", "kernel", "database", "postgresql", "mysql",
    # Web platform, JS ecosystem, edge, CDNs, servers
    "npm", "node.js", "nodejs", "javascript", "typescript",
    "react", "react.js", "react native", "next.js", "nextjs", "vue", "vue.js", "angular", "svelte",
    "vercel", "netlify", "cloudflare", "fastly", "akamai",
    "nginx", "apache", "caddy", "haproxy", "traefik",
    "cdn", "edge computing", "serverless", "wasm", "webassembly",
    "terraform", "pulumi", "ansible",
    "ci/cd", "github actions", "gitlab", "jenkins", "circleci",
    "redis", "mongodb", "elasticsearch", "kafka", "rabbitmq",
    "bun", "deno", "webpack", "vite",
    # Hardware / chips
    "semiconductor", "processor", "chip", "intel", "amd", "apple silicon",
    # Enterprise / SaaS
    "enterprise", "saas", "startup",
    # Big tech (common in IT headlines)
    "microsoft", "apple", "google", "meta", "amazon", "samsung",
]

_TRACKING_QUERY_KEYS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "utm_id", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid",
    "ref", "ref_src", "source", "spm", "si",
})

_TECH_KEYWORD_PATTERNS = [
    re.compile(r"\b" + re.escape(kw.strip().lower()) + r"\b")
    for kw in TECH_KEYWORDS
    if kw.strip()
]

# Near-duplicate headlines across syndicated feeds (wording differs slightly).
_FUZZY_TITLE_RATIO = 0.86
_FUZZY_MIN_CHARS = 28
_FUZZY_MIN_WORDS = 4


def _title_word_count(normalized: str) -> int:
    return len(normalized.split()) if normalized else 0


def titles_are_fuzzy_duplicates(a: str, b: str) -> bool:
    """True if normalized titles are likely the same story (SequenceMatcher)."""
    if not a or not b or a == b:
        return False
    la, lb = len(a), len(b)
    if not la or not lb:
        return False
    shorter, longer = min(la, lb), max(la, lb)
    if shorter / longer < 0.65:
        return False
    if la < _FUZZY_MIN_CHARS or lb < _FUZZY_MIN_CHARS:
        return False
    if _title_word_count(a) < _FUZZY_MIN_WORDS or _title_word_count(b) < _FUZZY_MIN_WORDS:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= _FUZZY_TITLE_RATIO


def normalize_feed_url(url: str) -> str:
    """Strip tracking params and trivial differences for cross-feed deduplication."""
    if not url or not url.strip():
        return ""
    raw = url.strip()
    try:
        parsed = urlparse(raw)
        pairs = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in _TRACKING_QUERY_KEYS
        ]
        query = urlencode(pairs)
        netloc = (parsed.netloc or "").lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        scheme = (parsed.scheme or "https").lower()
        path = parsed.path or "/"
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return raw.lower()


def normalize_title_for_dedupe(title: str) -> str:
    """Collapse title for syndication-style duplicate detection."""
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def dedupe_news_items(items: List[NewsItem]) -> List[NewsItem]:
    """
    Drop repeats across feeds. Assumes items are sorted newest-first.
    Skips duplicate normalized URLs, identical normalized titles, or fuzzy title matches.
    """
    seen_urls: set = set()
    seen_titles: set = set()
    kept_title_norms: List[str] = []
    out: List[NewsItem] = []
    for item in items:
        key_url = normalize_feed_url(item.link)
        if not key_url:
            key_url = item.link.strip()
        if key_url in seen_urls:
            continue
        nt = normalize_title_for_dedupe(item.title)
        if nt and nt in seen_titles:
            continue
        if nt:
            if any(titles_are_fuzzy_duplicates(nt, prev) for prev in kept_title_norms):
                continue
        seen_urls.add(key_url)
        if nt:
            seen_titles.add(nt)
            kept_title_norms.append(nt)
        out.append(item)
    return out


def text_matches_tech_keywords(text: str) -> bool:
    """True if title/snippet matches any tech keyword (word-boundary aware)."""
    lowered = text.lower()
    return any(p.search(lowered) for p in _TECH_KEYWORD_PATTERNS)


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
    
    with ThreadPoolExecutor(max_workers=10) as executor:
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
    before = len(all_news)
    all_news = dedupe_news_items(all_news)
    dropped = before - len(all_news)
    if dropped:
        logger.debug(f"Deduped {dropped} duplicate story(ies) across feeds")
    return all_news


def filter_tech_news(news_items: List[NewsItem]) -> List[NewsItem]:
    """Filter news items for AI and broader IT/tech relevance."""
    filtered = []
    
    for item in news_items:
        text = item.title + " " + item.snippet
        if text_matches_tech_keywords(text):
            filtered.append(item)
    
    return filtered


def get_latest_news(limit: int = 10) -> List[NewsItem]:
    """Get the latest tech news items (keyword-filtered)."""
    all_news = fetch_all_news()
    tech_news = filter_tech_news(all_news)
    return tech_news[:limit]


if __name__ == "__main__":
    news = get_latest_news(5)
    for item in news:
        logger.info(f"[{item.source}] {item.title}")
        logger.info(f"   {item.link}")