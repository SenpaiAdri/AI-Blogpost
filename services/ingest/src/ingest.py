import difflib
import feedparser
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
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


# Relevance scope: AI + software engineering (+ security only with an AI/dev angle).
# Tiered matching fixes an over-broad OR gate where a single adjacent term
# ("startup", "apple", "patch", "quantum", ...) alone passed the filter and
# produced general-tech posts (Startup Battlefield guides, iOS betas, game
# removals, quantum/robotics, earnings) that are out of scope for devs.
#
# - CORE_* alone passes: AI terms and SWE terms are sufficient relevance.
# - ADJACENT_* requires a CORE co-signal in the same title+snippet: big-tech
#   names, security/infra/hardware, enterprise/SaaS, quantum/robotics only
#   count when paired with AI or SWE (e.g. "Apple AI coding assistant" passes,
#   "Apple Maps towns" fails; "prompt-injection flaw in LangChain" passes,
#   "Windows Patch Tuesday" fails).
CORE_AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "neural networks", "neural",
    "llm", "large language model", "small language model", "slm",
    "generative ai", "generative", "stable diffusion", "diffusion model",
    "multimodal", "agentic", "ai agent", "ai agents", "ai assistant",
    "reasoning model", "foundation model", "frontier model",
    "gpt", "chatgpt", "openai", "anthropic", "claude", "gemini",
    "deepmind", "llama", "gemma", "mistral", "deepseek",
    "hugging face", "cohere", "perplexity", "midjourney", "runway",
    "stability ai", "grok", "qwen", "kimi", "phi",
    "transformer", "embeddings", "embedding model",
    "rag", "retrieval-augmented", "retrieval augmented",
    "vector database", "vector db",
    "prompt engineering", "fine-tuning", "finetuning", "finetune", "rlhf",
    "pytorch", "tensorflow", "jax", "langchain", "llamaindex", "ollama",
    "copilot", "chatbot", "voice agent", "coding agent",
    "text-to-image", "text to image", "image generation", "video generation",
    "edge ai", "physical ai", "artificial general intelligence", "agi",
]

CORE_SWE_KEYWORDS = [
    "developer", "developers", "programmer", "programming", "coding",
    "software development", "software engineer", "software engineering",
    "software architecture", "open source", "github", "gitlab", "git",
    "pull request", "code review", "devtools", "developer tools",
    "programming language", "api", "sdk", "framework", "library",
    "ide", "vscode", "vs code",
    "python", "javascript", "typescript", "rust", "golang", "kotlin",
    "swift", "ruby", "php", "scala", "haskell", "elixir", "dart",
    "npm", "node.js", "nodejs", "deno", "bun",
    "react", "react.js", "react native", "next.js", "nextjs",
    "vue", "vue.js", "angular", "svelte", "vite", "webpack",
    "flutter", "tailwind",
    "linux", "kernel", "ubuntu",
    "database", "postgresql", "postgres", "mysql", "sqlite",
    "redis", "mongodb", "elasticsearch", "kafka", "rabbitmq",
    "docker", "kubernetes", "terraform", "pulumi", "ansible", "devops",
    "ci/cd", "github actions", "gitlab ci", "jenkins", "circleci",
    "serverless", "wasm", "webassembly",
    "refactor", "refactoring", "debugging", "unit test", "integration test",
]

CORE_KEYWORDS = CORE_AI_KEYWORDS + CORE_SWE_KEYWORDS

ADJACENT_SECURITY_KEYWORDS = [
    "security", "cybersecurity", "infosec",
    "ransomware", "vulnerability", "breach", "malware",
    "patch", "encryption", "privacy", "phishing",
    "zero-day", "zeroday", "deepfake", "supply chain attack", "pqc",
    "identity", "oauth", "sso", "mfa",
    "infostealer", "data breach", "threat", "exploit", "cve",
    "firewall", "pentest", "penetration test",
]

ADJACENT_INFRA_KEYWORDS = [
    "cloud", "server", "datacenter", "data center", "infrastructure",
    "aws", "azure", "gcp", "google cloud",
    "cdn", "edge computing",
    "vercel", "netlify", "cloudflare", "fastly", "akamai",
    "nginx", "apache", "caddy", "haproxy", "traefik",
]

ADJACENT_HARDWARE_KEYWORDS = [
    "semiconductor", "processor", "chip", "intel", "amd",
    "apple silicon", "nvidia", "gpu", "cuda", "tpu", "npu", "asic",
    "hardware",
]

ADJACENT_BIGTECH_KEYWORDS = [
    "microsoft", "apple", "google", "meta", "amazon", "samsung", "alphabet",
]

ADJACENT_BUSINESS_KEYWORDS = [
    "enterprise", "saas", "startup", "startups", "funding",
    "venture capital", "series a", "series b", "ipo", "earnings",
]

ADJACENT_EMERGING_KEYWORDS = [
    "quantum", "qubit", "qpu", "quantum computing", "quantum computer",
    "robotics", "robot", "humanoid", "drone",
]

ADJACENT_KEYWORDS = (
    ADJACENT_SECURITY_KEYWORDS
    + ADJACENT_INFRA_KEYWORDS
    + ADJACENT_HARDWARE_KEYWORDS
    + ADJACENT_BIGTECH_KEYWORDS
    + ADJACENT_BUSINESS_KEYWORDS
    + ADJACENT_EMERGING_KEYWORDS
)

# Kept for backward compatibility (combined vocabulary). Matching logic below
# is tiered: CORE alone passes, ADJACENT requires a CORE co-signal.
TECH_KEYWORDS = CORE_KEYWORDS + ADJACENT_KEYWORDS

_TRACKING_QUERY_KEYS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "utm_id", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid",
    "ref", "ref_src", "source", "spm", "si",
})

def _compile_keyword_patterns(keywords) -> list:
    return [
        re.compile(r"\b" + re.escape(kw.strip().lower()) + r"\b")
        for kw in keywords
        if kw.strip()
    ]


_CORE_KEYWORD_PATTERNS = _compile_keyword_patterns(CORE_KEYWORDS)

_ADJACENT_KEYWORD_PATTERNS = _compile_keyword_patterns(ADJACENT_KEYWORDS)

# Legacy combined patterns (kept for backward compat / debugging).
_TECH_KEYWORD_PATTERNS = _compile_keyword_patterns(TECH_KEYWORDS)

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


def text_matches_core_keywords(text: str) -> bool:
    """True if text contains an AI or SWE core term (word-boundary aware)."""
    lowered = (text or "").lower()
    return any(p.search(lowered) for p in _CORE_KEYWORD_PATTERNS)


def text_matches_adjacent_keywords(text: str) -> bool:
    """True if text contains an adjacent (context-dependent) term."""
    lowered = (text or "").lower()
    return any(p.search(lowered) for p in _ADJACENT_KEYWORD_PATTERNS)


def text_matches_tech_keywords(text: str) -> bool:
    """True if title/snippet is in scope for AI + SWE ingestion.

    Tiered rule: a CORE AI/SWE term must be present. Adjacent terms
    (big-tech names, security/infra/hardware, enterprise/SaaS,
    quantum/robotics) alone do NOT pass — they only count with a CORE
    co-signal in the same text. This keeps "Apple AI coding assistant"
    while rejecting "Apple Maps towns" or "Startup Battlefield guide".
    """
    lowered = (text or "").lower()
    return any(p.search(lowered) for p in _CORE_KEYWORD_PATTERNS)


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


def filter_tech_news(news_items: List[NewsItem]) -> List[NewsItem]:
    """Filter news items for AI + software engineering relevance.

    Security/infra/hardware/big-tech/quantum/robotics items only pass with
    an AI or SWE core co-signal in the same title+snippet (see
    text_matches_tech_keywords). Pure IT-sec patches, cloud/infra updates,
    chip earnings, startup guides, and consumer-tech stories are rejected.
    """
    filtered = []

    for item in news_items:
        text = item.title + " " + item.snippet
        if text_matches_tech_keywords(text):
            filtered.append(item)
    
    return filtered


def get_latest_news(limit: int = 10, active_topics: Optional[List[Any]] = None, rss_feeds: Optional[List[Dict]] = None) -> List[NewsItem]:
    """Get the latest tech news items (keyword-filtered)."""
    all_news = fetch_all_news(rss_feeds)
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