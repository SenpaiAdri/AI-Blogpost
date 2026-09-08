"""Safe URL-slug generation."""

import re

from config import MAX_SLUG_LENGTH


def generate_safe_slug(title: str) -> str:
    """Generate safe URL slug from title."""
    slug = (title or "").lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')[:MAX_SLUG_LENGTH]
    return slug or "untitled"


def slugify_tag(tag_name: str) -> str:
    """Slugify a tag name (shared by single + batch post persistence)."""
    slug = (tag_name or "").lower().replace(" ", "-")
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug
