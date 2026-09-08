"""Admin topic-guidance matching and prioritization."""

import re
from typing import Any, List, Optional

from selection.models import ActiveTopic, NewsItem


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
