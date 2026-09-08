"""Candidate selection: RSS fetch -> relevance filter -> dedupe -> prioritize.

Public entry point is :func:`feeds.get_latest_news`.
"""

from selection.models import ActiveTopic, NewsItem  # noqa: F401 (re-export)

__all__ = ["ActiveTopic", "NewsItem"]
