"""Pipeline orchestration: fetch -> process -> persist -> summarize."""

from pipeline.formatting import format_context_for_ai  # noqa: F401
from pipeline.orchestrator import main, validate_environment  # noqa: F401
from pipeline.persistence import batch_save_posts, save_post  # noqa: F401
from pipeline.processor import process_news_item, process_news_item_for_batch  # noqa: F401
from pipeline.sources import resolve_display_source_name  # noqa: F401

__all__ = [
    "main",
    "validate_environment",
    "process_news_item",
    "process_news_item_for_batch",
    "save_post",
    "batch_save_posts",
    "format_context_for_ai",
    "resolve_display_source_name",
]
