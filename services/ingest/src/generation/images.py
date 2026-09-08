"""Inline-image policy: strip, verify reachability, enforce allowlist, attribute."""

import re
from typing import List
from urllib.parse import urlparse

import requests

import config
from infra.logger import get_logger

logger = get_logger("generator")

# Snapshotted from config at import (tests override these module attrs directly).
_VERIFY_INLINE_IMAGES = config.VERIFY_INLINE_IMAGES
_IMAGE_URL_CHECK_TIMEOUT_SECONDS = config.IMAGE_URL_CHECK_TIMEOUT_SECONDS
_STRIP_MARKDOWN_IMAGES = config.STRIP_MARKDOWN_IMAGES
_INLINE_IMAGE_ALLOWED_DOMAINS: set = set(config.ALLOW_INLINE_IMAGE_DOMAINS)

_IMAGE_URL_CHECK_CACHE: dict[str, bool] = {}

_MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _image_tail_already_attributed(tail: str) -> bool:
    """True if the text right after an image markdown already credits the source."""
    t = tail.lstrip()
    if not t:
        return False
    if t[0] in "*_":
        head = t[:160].lower()
        if "photo" in head or "source" in head or "credit" in head or "original" in head:
            return True
    return False


def _image_url_is_fetchable(url: str) -> bool:
    """Best-effort check that a URL responds as an image."""
    if not url:
        return False
    if url in _IMAGE_URL_CHECK_CACHE:
        return _IMAGE_URL_CHECK_CACHE[url]

    ok = False
    try:
        response = requests.head(url, allow_redirects=True, timeout=_IMAGE_URL_CHECK_TIMEOUT_SECONDS)
        content_type = (response.headers.get("content-type") or "").lower()
        if response.status_code < 400 and content_type.startswith("image/"):
            ok = True
        elif response.status_code < 400:
            # Some origins don't expose useful HEAD content-type; try GET fallback.
            response = requests.get(url, stream=True, allow_redirects=True, timeout=_IMAGE_URL_CHECK_TIMEOUT_SECONDS)
            content_type = (response.headers.get("content-type") or "").lower()
            ok = response.status_code < 400 and content_type.startswith("image/")
    except Exception:
        ok = False

    _IMAGE_URL_CHECK_CACHE[url] = ok
    return ok


def _image_domain_is_allowed(url: str) -> bool:
    """Allow inline image embeds only from configured domains when set."""
    if not _INLINE_IMAGE_ALLOWED_DOMAINS:
        return True
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return False
    host = host.split(":")[0]
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in _INLINE_IMAGE_ALLOWED_DOMAINS)


def process_inline_images(content: str, source_name: str, source_url: str) -> str:
    """Strip hotlinked images or append attribution pointing at the cited article."""
    if not content:
        return content

    if _STRIP_MARKDOWN_IMAGES:

        def strip_repl(match: re.Match) -> str:
            alt = (match.group(1) or "").strip() or "Photo"
            label = source_name or "original article"
            if source_url.strip():
                return (
                    f"*{alt}: not embedded on this site; "
                    f"[open the original article ({label})]({source_url}) to view it.*"
                )
            return f"*{alt} (image omitted).*"

        return _MARKDOWN_IMAGE.sub(strip_repl, content)

    if not source_url.strip():
        return content

    parts: List[str] = []
    last = 0
    label = source_name.strip() or "Original article"
    for m in _MARKDOWN_IMAGE.finditer(content):
        alt = (m.group(1) or "").strip() or "Photo"
        image_url = (m.group(2) or "").strip()
        if not _image_domain_is_allowed(image_url):
            label = source_name.strip() or "original article"
            parts.append(content[last : m.start()])
            if source_url.strip():
                parts.append(
                    f"*{alt}: image omitted due to site embedding policy; "
                    f"[open the original article ({label})]({source_url}) to view it.*"
                )
            else:
                parts.append(f"*{alt} (image omitted due to site embedding policy).*")
            last = m.end()
            continue

        if _VERIFY_INLINE_IMAGES and not _image_url_is_fetchable(image_url):
            label = source_name.strip() or "original article"
            if source_url.strip():
                parts.append(content[last : m.start()])
                parts.append(
                    f"*{alt}: image not available from source CDN right now; "
                    f"[open the original article ({label})]({source_url}) to view context.*"
                )
            else:
                parts.append(content[last : m.start()])
                parts.append(f"*{alt} (image omitted; original image URL unavailable).*")
            last = m.end()
            continue

        parts.append(content[last : m.end()])
        tail = content[m.end() : m.end() + 800]
        if source_url in tail or _image_tail_already_attributed(tail):
            last = m.end()
            continue
        parts.append(
            f"\n\n*Image: shown as in source reporting. "
            f"Credit and license belong to the rights holder; see "
            f"[{label}]({source_url}) for the original context.*\n\n"
        )
        last = m.end()
    parts.append(content[last:])
    return "".join(parts)
