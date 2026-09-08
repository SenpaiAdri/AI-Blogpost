"""Tiered relevance filter: CORE AI/SWE terms pass, ADJACENT needs CORE co-signal."""

from typing import List

from selection.keywords import _ADJACENT_KEYWORD_PATTERNS, _CORE_KEYWORD_PATTERNS
from selection.models import NewsItem


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
