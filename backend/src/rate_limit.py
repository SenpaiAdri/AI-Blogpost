import os
import time
import threading
from urllib.parse import urlparse

from logger import get_logger

logger = get_logger("rate_limit")


def _float_env(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.01)
    except (TypeError, ValueError):
        return default


class DomainRateLimiter:
    """Simple per-domain limiter using minimum interval between requests."""

    def __init__(self, default_rps: float):
        self.default_rps = max(default_rps, 0.01)
        self._lock = threading.Lock()
        self._next_allowed_by_domain: dict[str, float] = {}

    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower() or "unknown"
        except Exception:
            return "unknown"

    def _rps_for_domain(self, domain: str) -> float:
        # Environment overrides, e.g. RATE_LIMIT_RPS_OPENAI_COM=1.0
        env_key = "RATE_LIMIT_RPS_" + domain.replace(".", "_").replace("-", "_").upper()
        return _float_env(env_key, self.default_rps)

    def wait(self, url: str) -> None:
        domain = self._extract_domain(url)
        rps = self._rps_for_domain(domain)
        min_interval = 1.0 / rps

        with self._lock:
            now = time.monotonic()
            next_allowed = self._next_allowed_by_domain.get(domain, now)
            sleep_for = max(next_allowed - now, 0.0)

            reservation_time = now + sleep_for
            self._next_allowed_by_domain[domain] = reservation_time + min_interval

        if sleep_for > 0:
            logger.debug(f"Throttling {domain} for {sleep_for:.2f}s")
            time.sleep(sleep_for)


DEFAULT_RPS = _float_env("RATE_LIMIT_RPS_DEFAULT", 2.0)
domain_rate_limiter = DomainRateLimiter(default_rps=DEFAULT_RPS)


def wait_for_url(url: str) -> None:
    """Public helper used by network-bound modules."""
    domain_rate_limiter.wait(url)
