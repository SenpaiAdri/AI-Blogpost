import difflib
import feedparser
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from config import (
    FUZZY_TITLE_RATIO,
    FUZZY_MIN_CHARS,
    FUZZY_MIN_WORDS,
    MAX_PER_SOURCE,
    MAX_CANDIDATES,
    FETCH_ITEMS_PER_FEED,
    MAX_FEED_WORKERS,
    RSS_TIMEOUT_SECONDS,
)
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


@dataclass(frozen=True)
class ActiveTopic:
    id: str
    keyword: str
    normalized_keyword: str
    weight: int = 1


# Title/snippet must match at least one keyword using word boundaries (see _TECH_KEYWORD_PATTERNS).
# Avoid very short ambiguous tokens (e.g. "it", "go").
TECH_KEYWORDS = [
    # AI / ML
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "gpt", "llm", "neural", "chatgpt", "openai", "anthropic", "deepmind",
    "gemini", "claude", "llama", "gemma", "mistral", "nvidia", "stable diffusion",
    "large language model", "generative", "deepseek", "multimodal", "agentic",
    "slm", "small language model", "edge ai", "physical ai", "reasoning model",
    # Security / IT operations
    "security", "cybersecurity", "ransomware", "vulnerability", "breach", "malware",
    "patch", "encryption", "privacy", "phishing", "zero-day", "zeroday",
    "deepfake", "supply chain attack", "pqc", "identity",
    "infostealer", "data breach", "threat", "exploit", "cve",
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
    "semiconductor", "processor", "chip", "intel", "amd", "apple silicon", "nvidia", "gpu", "cuda",
    # Robotics / Physical AI
    "robotics", "robot", "humanoid", "drone",
    # Quantum computing
    "quantum", "qubit", "qpu", "quantum computing", "quantum computer",
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

# Fuzzy duplicate configs now loaded from config.py

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
    if la < FUZZY_MIN_CHARS or lb < FUZZY_MIN_CHARS:
        return False
    if _title_word_count(a) < FUZZY_MIN_WORDS or _title_word_count(b) < FUZZY_MIN_WORDS:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= FUZZY_TITLE_RATIO


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
    - Same URL: skip (exact duplicate)
    - Same title + same source: skip (exact duplicate from source)
    - Similar title + same source: skip (fuzzy duplicate from source)
    - Different source: KEEP ALL (trending topics should be covered from multiple sources)
    """
    seen_urls: set = set()
    seen_titles_by_source: dict = {}
    kept_titles: List[tuple] = []
    out: List[NewsItem] = []
    skipped_url = 0
    skipped_same_source = 0
    
    for item in items:
        source = (item.source or "unknown").strip().lower()
        key_url = normalize_feed_url(item.link)
        if not key_url:
            key_url = item.link.strip()
        
        # Skip exact URL duplicates
        if key_url in seen_urls:
            skipped_url += 1
            continue
        seen_urls.add(key_url)
        
        nt = normalize_title_for_dedupe(item.title)
        
        # Track titles per source
        if nt:
            if nt not in seen_titles_by_source:
                seen_titles_by_source[nt] = set()
            
            # Skip if same title AND same source
            if source in seen_titles_by_source[nt]:
                skipped_same_source += 1
                continue
            
            # Check fuzzy duplicate ONLY for same source (allow multi-source trending topics)
            if any(titles_are_fuzzy_duplicates(nt, prev_title) for prev_title, prev_source in kept_titles if prev_source == source):
                skipped_same_source += 1
                continue
            
            seen_titles_by_source[nt].add(source)
            kept_titles.append((nt, source))
        
        out.append(item)
    
    total_skipped = skipped_url + skipped_same_source
    if total_skipped > 0:
        logger.info(f"  Dedupe: skipped {skipped_url} url, {skipped_same_source} same-source duplicate(s), kept {len(out)} items")
    return out


def text_matches_tech_keywords(text: str) -> bool:
    """True if title/snippet matches any tech keyword (word-boundary aware)."""
    lowered = text.lower()
    return any(p.search(lowered) for p in _TECH_KEYWORD_PATTERNS)


def normalize_topic_keyword(keyword: str) -> str:
    """Normalize admin guidance keywords for deterministic matching."""
    return re.sub(r"\s+", " ", (keyword or "").strip()).lower()


def coerce_active_topics(active_topics: Optional[List[Any]]) -> List[ActiveTopic]:
    """Accept Supabase dict rows or ActiveTopic values and normalize for matching."""
    topics: List[ActiveTopic] = []
    for topic in active_topics or []:
        if isinstance(topic, ActiveTopic):
            normalized = normalize_topic_keyword(topic.normalized_keyword or topic.keyword)
            if normalized:
                topics.append(ActiveTopic(topic.id, topic.keyword, normalized, max(1, min(topic.weight, 5))))
            continue

        if isinstance(topic, dict):
            keyword = str(topic.get("keyword") or "").strip()
            normalized = normalize_topic_keyword(str(topic.get("normalized_keyword") or keyword))
            topic_id = str(topic.get("id") or normalized)
            try:
                weight = int(topic.get("weight") or 1)
            except (TypeError, ValueError):
                weight = 1
            if normalized:
                topics.append(ActiveTopic(topic_id, keyword or normalized, normalized, max(1, min(weight, 5))))
    return topics


def _topic_pattern(topic: ActiveTopic) -> re.Pattern:
    return re.compile(r"\b" + re.escape(topic.normalized_keyword) + r"\b", re.IGNORECASE)


def matched_topic_ids(item: NewsItem, active_topics: Optional[List[Any]]) -> List[str]:
    """Return active topic IDs matched in title or snippet."""
    text = f"{item.title} {item.snippet}"
    return [
        topic.id
        for topic in coerce_active_topics(active_topics)
        if _topic_pattern(topic).search(text)
    ]


def prioritize_news_items_by_topics(items: List[NewsItem], active_topics: Optional[List[Any]]) -> List[NewsItem]:
    """Stable-sort matched items ahead of others using bounded topic weights."""
    topics = coerce_active_topics(active_topics)
    if not topics:
        return items

    def boost(item: NewsItem) -> int:
        text = f"{item.title} {item.snippet}"
        return sum(topic.weight for topic in topics if _topic_pattern(topic).search(text))

    return [
        item
        for _, item in sorted(
            enumerate(items),
            key=lambda pair: (-boost(pair[1]), pair[0]),
        )
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


def fetch_all_news() -> List[NewsItem]:
    """Fetch all RSS feeds in parallel and return combined, sorted news."""
    all_news = []
    failed_feeds = []
    
    with ThreadPoolExecutor(max_workers=MAX_FEED_WORKERS) as executor:
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


def get_latest_news(limit: int = 10, active_topics: Optional[List[Any]] = None) -> List[NewsItem]:
    """Get the latest tech news items (keyword-filtered)."""
    all_news = fetch_all_news()
    tech_news = filter_tech_news(all_news)
    prioritized = prioritize_news_items_by_topics(tech_news, active_topics)
    diversified = diversify_news_items(prioritized, limit=limit, max_per_source=MAX_PER_SOURCE)
    return diversified


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


def diversify_news_items(items: List[NewsItem], limit: int, max_per_source: int = 3) -> List[NewsItem]:
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


if __name__ == "__main__":
    news = get_latest_news(5)
    for item in news:
        logger.info(f"[{item.source}] {item.title}")
        logger.info(f"   {item.link}")