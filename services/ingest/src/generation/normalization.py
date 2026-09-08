"""Validate + normalize raw model JSON into the post schema."""

import html
import re
import threading
from typing import Any, Dict, List, Optional

from config import MAX_TAG_LENGTH, MAX_TAGS, MAX_TLDR_ITEMS, MAX_TLDR_LENGTH
from generation.cover import KEYWORD_MAP
from generation.markdown import sanitize_ai_content
from infra.logger import get_logger
from infra.metrics import register_summary_provider

logger = get_logger("generator")

_NORMALIZATION_FALLBACK_COUNTS: Dict[str, int] = {}
_NORMALIZATION_FALLBACK_BY_MODEL: Dict[str, Dict[str, int]] = {}
_NORMALIZATION_METRICS_LOCK = threading.Lock()


def _coerce_list_of_strings(value: Any) -> List[str]:
    """Normalize values to a non-empty list of strings."""
    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


_TAG_DISPLAY_NAMES = {
    "security": "Security",
    "cloud": "Cloud",
    "devops": "DevOps",
    "llm": "AI",
    "gpu": "Hardware",
    "ml": "AI",
    "robotics": "Robotics",
    "agent": "AI Agents",
    "research": "Research",
    "startup": "Startups",
    "hardware": "Hardware",
    "quantum": "Quantum",
}

_GENERIC_TAGS = {"tech news", "technology", "news", "breaking"}


def _fallback_tags(title: str, content: str, source_name: str = "") -> List[str]:
    """Derive specific fallback tags from known keyword/category mappings."""
    haystack = f"{title} {content[:1500]} {source_name}".lower()
    tags: List[str] = []
    for keyword, category in KEYWORD_MAP.items():
        if keyword in haystack:
            label = _TAG_DISPLAY_NAMES.get(category, category.title())
            if label not in tags:
                tags.append(label)
        if len(tags) >= MAX_TAGS:
            break

    if not tags:
        tags = ["Developer Tools"] if any(
            token in haystack for token in ("developer", "github", "open source", "programming")
        ) else ["Technology"]
    return tags[:MAX_TAGS]


def _normalize_tags(tags: List[str], title: str, content: str, source_name: str) -> List[str]:
    """Keep tags specific enough for topic filtering and avoid single generic tags."""
    cleaned: List[str] = []
    for tag in tags:
        safe = re.sub(r"\s+", " ", html.unescape(str(tag))).strip()
        if not safe:
            continue
        if safe.lower() in _GENERIC_TAGS:
            continue
        if safe not in cleaned:
            cleaned.append(safe[:MAX_TAG_LENGTH])

    fallback = _fallback_tags(title, content, source_name)
    for tag in fallback:
        if tag not in cleaned:
            cleaned.append(tag)

    return cleaned[:MAX_TAGS]


def _plain_text_from_markdown(content: str) -> str:
    """Produce readable text for excerpt fallback without markdown syntax."""
    text = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>|-]+", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _complete_sentence_excerpt(text: str, max_chars: int = 180) -> str:
    """Return a complete sentence without cutting off mid-thought."""
    cleaned = _plain_text_from_markdown(text)
    if not cleaned:
        return ""
    sentence_match = re.search(r"(.{40,}?[.!?])(?:\s|$)", cleaned)
    if sentence_match and len(sentence_match.group(1)) <= max_chars:
        return sentence_match.group(1).strip()

    snippet = cleaned[:max_chars].rstrip()
    boundary = max(snippet.rfind(", "), snippet.rfind("; "), snippet.rfind(": "), snippet.rfind(" "))
    if boundary >= 80:
        snippet = snippet[:boundary].rstrip()
    return snippet.rstrip(".!?;:,") + "."


def _record_normalization_fallbacks(
    model_name: str, fallback_fields: List[str], extra_keys: List[str]
) -> None:
    """Track how often we rely on fallback normalization fields."""
    if not fallback_fields and not extra_keys:
        return

    with _NORMALIZATION_METRICS_LOCK:
        for field in fallback_fields:
            _NORMALIZATION_FALLBACK_COUNTS[field] = (
                _NORMALIZATION_FALLBACK_COUNTS.get(field, 0) + 1
            )
            if model_name:
                if model_name not in _NORMALIZATION_FALLBACK_BY_MODEL:
                    _NORMALIZATION_FALLBACK_BY_MODEL[model_name] = {}
                model_bucket = _NORMALIZATION_FALLBACK_BY_MODEL[model_name]
                model_bucket[field] = model_bucket.get(field, 0) + 1
        if extra_keys:
            _NORMALIZATION_FALLBACK_COUNTS["extra_keys_dropped"] = (
                _NORMALIZATION_FALLBACK_COUNTS.get("extra_keys_dropped", 0)
                + len(extra_keys)
            )
            if model_name:
                if model_name not in _NORMALIZATION_FALLBACK_BY_MODEL:
                    _NORMALIZATION_FALLBACK_BY_MODEL[model_name] = {}
                model_bucket = _NORMALIZATION_FALLBACK_BY_MODEL[model_name]
                model_bucket["extra_keys_dropped"] = (
                    model_bucket.get("extra_keys_dropped", 0) + len(extra_keys)
                )

    logger.info(
        "    Normalization fallback used (%s): %s%s",
        model_name,
        ", ".join(fallback_fields) if fallback_fields else "none",
        f" | dropped extra keys: {', '.join(extra_keys)}" if extra_keys else "",
    )


def get_normalization_fallback_counts() -> Dict[str, int]:
    """Return a snapshot of normalization fallback counters for summaries."""
    with _NORMALIZATION_METRICS_LOCK:
        return dict(_NORMALIZATION_FALLBACK_COUNTS)


def get_normalization_fallbacks_by_model() -> Dict[str, Dict[str, int]]:
    """Return model-attributed fallback counters for summaries."""
    with _NORMALIZATION_METRICS_LOCK:
        return {
            model: dict(counts)
            for model, counts in _NORMALIZATION_FALLBACK_BY_MODEL.items()
            if counts
        }


def validate_and_normalize_result(
    result: Dict[str, Any],
    topic: str,
    source_name: str,
    source_url: str,
    fallback_fields: Optional[List[str]] = None,
    extra_keys: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Validate and normalize AI output to the expected schema."""
    if not isinstance(result, dict):
        return None

    fallback_log = fallback_fields if fallback_fields is not None else []
    extra_log = extra_keys if extra_keys is not None else []
    allowed_keys = {"title", "slug", "tldr", "content", "excerpt", "tags"}
    dropped_keys = sorted(str(k) for k in result.keys() if str(k) not in allowed_keys)
    extra_log.extend(dropped_keys)

    title = str(result.get("title", "")).strip() or topic.strip()
    if not str(result.get("title", "")).strip():
        fallback_log.append("title_defaulted")
    content = str(result.get("content", "")).strip()
    excerpt = str(result.get("excerpt", "")).strip()

    if not content:
        return None

    slug = str(result.get("slug", "")).strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        fallback_log.append("slug_regenerated")
        base = re.sub(r"[^a-z0-9-]", "-", title.lower())
        slug = re.sub(r"-+", "-", base).strip("-")[:80] or "post"

    tldr = _coerce_list_of_strings(result.get("tldr", []))
    # Enforce per-item length cap from config.
    tldr = [t[:MAX_TLDR_LENGTH] for t in tldr]
    if not tldr:
        fallback_log.append("tldr_defaulted")
        tldr = [f"Update: {title}", f"Source: {source_name or 'Tech news'}"]
    tldr = tldr[:MAX_TLDR_ITEMS]

    raw_tags = _coerce_list_of_strings(result.get("tags", []))
    tags = _normalize_tags(raw_tags, title, content, source_name)
    if not raw_tags or raw_tags == ["Tech News"]:
        fallback_log.append("tags_defaulted")
    tags = tags[:MAX_TAGS]
    if not excerpt:
        fallback_log.append("excerpt_defaulted")

    excerpt_text = _complete_sentence_excerpt(excerpt, 180)
    if not excerpt_text:
        excerpt_text = _complete_sentence_excerpt(content, 180)
    if not excerpt_text:
        excerpt_text = f"Technology update from {source_name or 'the source'}."

    normalized: Dict[str, Any] = {
        "title": title,
        "slug": slug,
        "tldr": tldr,
        "content": sanitize_ai_content(title, content, source_name, source_url),
        "excerpt": excerpt_text,
        "tags": tags,
        "source_url": [{"name": source_name, "url": source_url}],
    }
    return normalized


def finalize_result(
    result: Dict[str, Any],
    model_name: str,
    topic: str,
    source_name: str,
    source_url: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Optional[Dict[str, Any]]:
    """Validate, sanitize, and append common metadata."""
    fallback_fields: List[str] = []
    extra_keys: List[str] = []
    normalized = validate_and_normalize_result(
        result,
        topic,
        source_name,
        source_url,
        fallback_fields=fallback_fields,
        extra_keys=extra_keys,
    )
    if not normalized:
        logger.warning("    Generated payload failed schema validation")
        return None

    _record_normalization_fallbacks(model_name, fallback_fields, extra_keys)

    # Covers removed by editorial decision: no external image hotlinks on new
    # posts (copyright/hotlink risk). Column remains nullable for old rows.
    normalized["cover_image"] = None
    normalized["ai_model"] = model_name
    normalized["usage_metadata"] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }
    return normalized


register_summary_provider("normalization_fallbacks", get_normalization_fallback_counts)
register_summary_provider(
    "normalization_fallbacks_by_model", get_normalization_fallbacks_by_model
)
