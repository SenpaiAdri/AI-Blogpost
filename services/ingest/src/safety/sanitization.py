"""HTML / plain-text sanitization for storage and prompts."""

import html
import re
from html.parser import HTMLParser
from typing import List

from config import MAX_CONTENT_LENGTH


class HTMLSanitizer(HTMLParser):
    """Strip dangerous HTML tags while preserving safe formatting."""

    def __init__(self):
        super().__init__()
        self.output = []
        self.allowed_tags = {"p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
                           "ul", "ol", "li", "strong", "em", "code", "pre", "a", "blockquote"}

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if tag in self.allowed_tags:
            self.output.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.allowed_tags:
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.output.append(data)


def sanitize_html(content: str, max_length: int = MAX_CONTENT_LENGTH) -> str:
    """Sanitize HTML content - strip dangerous tags, limit length."""
    if not content:
        return ""

    try:
        parser = HTMLSanitizer()
        parser.feed(content)
        sanitized = "".join(parser.output)
    except Exception:
        sanitized = html.escape(content)

    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def sanitize_text(text: str, max_length: int = 5000) -> str:
    """Normalize plain text for storage and prompts: decode HTML entities, collapse whitespace, cap length."""
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def full_unescape(text: str) -> str:
    """Apply html.unescape until stable (handles double-encoded &amp;#x27;)."""
    prev = None
    current = text or ""
    while current != prev:
        prev = current
        current = html.unescape(current)
    return current
