#!/usr/bin/env python3
"""Decode HTML entities in post title, excerpt, and tldr (Supabase posts table).

Older rows may contain numeric entities (e.g. &#x27;) or double-encoded forms
(Estonia&amp;#x27;s) from the previous sanitize_text behavior. This script
applies repeated html.unescape until stable, then the same normalization as
validate_ai_output (whitespace collapse + length caps via security.sanitize_text).

Loads backend/.env. Requires SUPABASE_URL and SUPABASE_SERVICE_KEY (or
SUPABASE_SERVICE_ROLE_KEY).

  # Preview changes
  python backend/scripts/backfill_decode_entities.py --dry-run

  # Apply to all posts
  python backend/scripts/backfill_decode_entities.py

  # Only first 5 rows (smoke test)
  python backend/scripts/backfill_decode_entities.py --dry-run --limit 5

Requires backend dependencies: pip install -r backend/requirements.txt
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys


def _full_unescape(s: str) -> str:
    """Apply html.unescape until the string stops changing (handles &amp;#x27;)."""
    prev = None
    while s != prev:
        prev = s
        s = html.unescape(s)
    return s


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.normpath(os.path.join(root, "..", "src"))
    sys.path.insert(0, src)

    try:
        from database import get_supabase_client
        from security import MAX_EXCERPT_LENGTH, MAX_TITLE_LENGTH, sanitize_text
    except ModuleNotFoundError as exc:
        need = exc.name or "dependency"
        print(
            f'Missing Python module "{need}". Install backend dependencies:\n'
            "  python3 -m pip install -r backend/requirements.txt",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to Supabase",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Process at most N posts (0 = no limit)",
    )
    args = parser.parse_args()

    client = get_supabase_client()

    page_size = 200
    start = 0
    total_scanned = 0
    total_updated = 0
    processed_cap = args.limit if args.limit and args.limit > 0 else None

    while True:
        if processed_cap is not None and total_scanned >= processed_cap:
            break

        end = start + page_size - 1
        response = (
            client.from_("posts")
            .select("id, title, excerpt, tldr")
            .order("id")
            .range(start, end)
            .execute()
        )
        rows = response.data or []
        if not rows:
            break

        for row in rows:
            if processed_cap is not None and total_scanned >= processed_cap:
                break

            total_scanned += 1
            pid = row["id"]
            title_in = row.get("title") or ""
            excerpt_in = row.get("excerpt") or ""
            tldr_in = row.get("tldr")

            title_raw = _full_unescape(str(title_in))
            title_out = re.sub(r"\s+", " ", title_raw.strip())
            if len(title_out) > MAX_TITLE_LENGTH:
                title_out = title_out[:MAX_TITLE_LENGTH]

            excerpt_out = (
                sanitize_text(_full_unescape(str(excerpt_in)), MAX_EXCERPT_LENGTH)
                if excerpt_in
                else (excerpt_in or "")
            )

            if isinstance(tldr_in, list):
                tldr_out = [sanitize_text(_full_unescape(str(item)), 200) for item in tldr_in]
            elif tldr_in is None:
                tldr_out = None
            else:
                tldr_out = tldr_in

            changed = (
                title_out != title_in
                or excerpt_out != excerpt_in
                or tldr_out != tldr_in
            )

            if not changed:
                continue

            total_updated += 1
            if args.dry_run:
                print(f"[dry-run] would update id={pid} title={title_in[:60]!r}...")
                continue

            upd = {
                "title": title_out,
                "excerpt": excerpt_out,
                "tldr": tldr_out,
            }
            client.from_("posts").update(upd).eq("id", pid).execute()

        if len(rows) < page_size:
            break
        start += page_size

    mode = "dry-run" if args.dry_run else "applied"
    print(f"Done ({mode}): scanned={total_scanned}, rows_with_changes={total_updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
