"""SSRF-resistant URL validation and outbound-URL policy."""

import ipaddress
import os
from urllib.parse import urlparse

ALLOWED_PROTOCOLS = {"http", "https"}


def _get_allowed_domains() -> set[str]:
    raw = os.getenv("URL_ALLOWLIST_DOMAINS", "")
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


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
    return any(
        host == domain or host.endswith(f".{domain}") for domain in allowed_domains
    )


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
