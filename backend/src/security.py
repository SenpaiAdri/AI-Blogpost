import os
import re
import html
import ipaddress
from typing import Dict, Any, Optional, List
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_PROTOCOLS = {"http", "https"}
MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 50000
MAX_SLUG_LENGTH = 100
MAX_EXCERPT_LENGTH = 500


def _get_allowed_domains() -> set[str]:
    raw = os.getenv("URL_ALLOWLIST_DOMAINS", "")
    domains = {d.strip().lower() for d in raw.split(",") if d.strip()}
    return domains


def _is_private_or_special_ip(hostname: str) -> bool:
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False

    return any(
        [
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        ]
    )


def _host_matches_allowlist(hostname: str, allowed_domains: set[str]) -> bool:
    if not allowed_domains:
        return True

    host = hostname.lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


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


def validate_env_vars() -> tuple[bool, List[str]]:
    """Validate required environment variables exist."""
    required = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing = [v for v in required if not os.getenv(v)]
    return (len(missing) == 0, missing)


def validate_url(url: str) -> bool:
    """Validate URL is safe, well-formed, and SSRF-resistant."""
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_PROTOCOLS:
            return False
        if not parsed.netloc or not parsed.hostname:
            return False
        if any(x in parsed.netloc.lower() for x in ["javascript:", "data:", "blob:"]):
            return False
        if parsed.username or parsed.password:
            return False

        hostname = parsed.hostname.lower()

        if hostname in {"localhost", "localhost.localdomain"}:
            return False
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            return False
        if _is_private_or_special_ip(hostname):
            return False

        allowed_domains = _get_allowed_domains()
        if not _host_matches_allowlist(hostname, allowed_domains):
            return False

        return True
    except Exception:
        return False


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
    """Sanitize plain text - escape HTML, limit length."""
    if not text:
        return ""
    
    text = html.escape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


def generate_safe_slug(title: str) -> str:
    """Generate safe URL slug from title."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')[:MAX_SLUG_LENGTH]
    return slug or "untitled"


def validate_ai_output(data: Dict[str, Any]) -> Optional[str]:
    """Validate AI output matches expected schema. Returns error message if invalid."""
    if not isinstance(data, dict):
        return "Output is not a dictionary"
    
    required_fields = ["title", "slug", "content"]
    for field in required_fields:
        if field not in data or not data[field]:
            return f"Missing required field: {field}"
    
    if not isinstance(data.get("title"), str):
        return "Title must be a string"
    
    if len(data["title"]) > MAX_TITLE_LENGTH:
        return f"Title exceeds {MAX_TITLE_LENGTH} characters"
    
    if not isinstance(data.get("content"), str) or len(data["content"]) < 50:
        return "Content must be at least 50 characters"
    
    if len(data["content"]) > MAX_CONTENT_LENGTH:
        data["content"] = data["content"][:MAX_CONTENT_LENGTH]
    
    data["slug"] = generate_safe_slug(data.get("slug", data["title"]))
    
    if "excerpt" in data and data["excerpt"]:
        data["excerpt"] = data["excerpt"][:MAX_EXCERPT_LENGTH]
    else:
        data["excerpt"] = data["content"][:MAX_EXCERPT_LENGTH] + "..."
    
    if "tldr" in data and isinstance(data["tldr"], list):
        data["tldr"] = [sanitize_text(str(item), 200) for item in data["tldr"][:5]]
    
    if "tags" in data and isinstance(data["tags"], list):
        data["tags"] = [sanitize_text(str(tag), 50)[:30] for tag in data["tags"][:10]]
    
    return None