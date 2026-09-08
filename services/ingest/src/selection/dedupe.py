"""Cross-feed deduplication: URL + same-source title/fuzzy matching."""

import difflib
import re
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from config import ENABLE_FUZZY_DEDUP, FUZZY_MIN_CHARS, FUZZY_MIN_WORDS, FUZZY_TITLE_RATIO
from infra.logger import get_logger
from selection.models import NewsItem

logger = get_logger("ingest")

_TRACKING_QUERY_KEYS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "utm_id", "fbclid", "gclid", "mc_cid", "mc_eid", "igshid",
    "ref", "ref_src", "source", "spm", "si",
})


def _title_word_count(normalized: str) -> int:
    return len(normalized.split()) if normalized else 0


def titles_are_fuzzy_duplicates(a: str, b: str) -> bool:
    """True if normalized titles are likely the same story (SequenceMatcher)."""
    if not ENABLE_FUZZY_DEDUP:
        return False
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
