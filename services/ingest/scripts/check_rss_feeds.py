#!/usr/bin/env python3
"""Verify RSS_FEEDS URLs return HTTP 2xx. Exit 1 if any request fails."""

import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.normpath(os.path.join(root, "..", "src"))
    sys.path.insert(0, src)

    from rss_feeds import RSS_FEEDS

    failures = []
    for fc in RSS_FEEDS:
        name, url = fc["name"], fc["url"]
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ai-blogpost-feed-check/1.0"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status >= 400:
                    failures.append((name, url, resp.status, None))
        except urllib.error.HTTPError as e:
            failures.append((name, url, e.code, None))
        except Exception as e:
            failures.append((name, url, None, str(e)))

    if failures:
        for name, url, code, err in failures:
            if code is not None:
                print(f"FAIL [{code}] {name}: {url}", file=sys.stderr)
            else:
                print(f"FAIL [error] {name}: {url} — {err}", file=sys.stderr)
        return 1

    print(f"OK: {len(RSS_FEEDS)} feeds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
