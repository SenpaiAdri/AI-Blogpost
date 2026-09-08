"""Build the LLM context block from a NewsItem + scraped article."""

from typing import Optional

from config import MAX_TITLE_LENGTH
from safety.sanitization import sanitize_text
from safety.url_validation import validate_url
from selection.models import NewsItem


def format_context_for_ai(item: NewsItem, article_content: str = "", source_name: Optional[str] = None) -> str:
    """Format news item and article content for AI context."""
    sanitized_title = sanitize_text(item.title, MAX_TITLE_LENGTH)
    sanitized_link = item.link if validate_url(item.link) else ""
    sanitized_source = sanitize_text(source_name or item.source, 50)

    context = f"""Source: {sanitized_source}
Title: {sanitized_title}
Link: {sanitized_link}
Date: {item.pub_date.isoformat()}
"""
    if article_content:
        sanitized_content = sanitize_text(article_content, 4000)
        context += f"\nArticle Content:\n{sanitized_content}"
    else:
        sanitized_snippet = sanitize_text(item.snippet, 1000)
        context += f"\nSnippet: {sanitized_snippet}"

    return context
