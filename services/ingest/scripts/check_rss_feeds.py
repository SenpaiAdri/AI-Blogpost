#!/usr/bin/env python3
"""Verify RSS_FEEDS URLs return HTTP 2xx. Exit 1 if any request fails.

Failure policy (transient vs permanent):
- Transient failures (HTTP 429/5xx, timeouts, connection/DNS errors) are
  retried with exponential backoff before counting as failures, so a
  momentary rate-limit or network blip doesn't fail the run.
- Permanent failures (other 4xx such as 404/410) fail fast with no retry:
  the feed is gone or moved and a human must fix the URL or remove the
  feed. Silently accepting dead feeds rots the registry unnoticed.

Any feed still failing after retries exits 1 so the workflow stays red
until someone acts on it.
"""

import os
import sys
import time
import urllib.error
import urllib.request

MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 25
USER_AGENT = "ai-blogpost-feed-check/1.0"

# HTTP statuses worth retrying: rate-limit, timeout-ish, server-side.
_RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def is_retryable_status(code) -> bool:
    """True for HTTP statuses that may clear on their own (retry them)."""
    try:
        return int(code) in _RETRYABLE_STATUS
    except (TypeError, ValueError):
        return False


def check_feed(name: str, url: str):
    """Check one feed URL. Returns (ok: bool, detail: str for reporting)."""
    last_detail = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                if resp.status >= 400:
                    last_detail = f"HTTP {resp.status}"
                    if is_retryable_status(resp.status) and attempt < MAX_ATTEMPTS:
                        time.sleep(BASE_BACKOFF_SECONDS * attempt)
                        continue
                    return False, last_detail
                return True, f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            # NOTE: HTTPError subclasses URLError, so it must be caught first.
            last_detail = f"HTTP {e.code}"
            if is_retryable_status(e.code) and attempt < MAX_ATTEMPTS:
                time.sleep(BASE_BACKOFF_SECONDS * attempt)
                continue
            return False, last_detail
        except Exception as e:
            # Timeouts, DNS failures, refused/reset connections: transient
            # (a typo'd domain fails persistently and still fails loudly
            # after retries are exhausted).
            last_detail = f"{type(e).__name__}: {e}"
            if attempt < MAX_ATTEMPTS:
                time.sleep(BASE_BACKOFF_SECONDS * attempt)
                continue
            return False, last_detail
    return False, last_detail


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.normpath(os.path.join(root, "..", "src"))
    sys.path.insert(0, src)

    from selection.rss_feeds import RSS_FEEDS

    failures = []
    for fc in RSS_FEEDS:
        name, url = fc["name"], fc["url"]
        ok, detail = check_feed(name, url)
        if ok:
            print(f"OK   [{detail}] {name}: {url}")
        else:
            print(f"FAIL [{detail}] {name}: {url}", file=sys.stderr)
            failures.append((name, url, detail))

    succeeded = len(RSS_FEEDS) - len(failures)
    if failures:
        print(
            f"RESULT: {succeeded}/{len(RSS_FEEDS)} feeds healthy, "
            f"{len(failures)} failing (see FAIL lines above)",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(RSS_FEEDS)} feeds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
