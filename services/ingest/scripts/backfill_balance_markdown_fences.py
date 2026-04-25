#!/usr/bin/env python3
"""Close unbalanced ``` markdown fences in posts.content (Supabase).

When the model omits a closing fence, or closes it only at the end of the post
after prose and images, the article parses as one giant code block. This script
runs generator.normalize_markdown_fences (repair leaked prose/images inside fences,
then balance odd ``` counts) — same as ingest after fix_code_blocks.

Loads services/ingest/.env. Requires SUPABASE_URL and SUPABASE_SERVICE_KEY (or
SUPABASE_SERVICE_ROLE_KEY).

  # Preview changes
  python services/ingest/scripts/backfill_balance_markdown_fences.py --dry-run

  # Apply to all posts
  python services/ingest/scripts/backfill_balance_markdown_fences.py

  # Smoke test on first 5 rows
  python services/ingest/scripts/backfill_balance_markdown_fences.py --dry-run --limit 5

Requires ingest dependencies: pip install -r services/ingest/requirements.txt
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.normpath(os.path.join(root, "..", "src"))
    sys.path.insert(0, src)

    try:
        from database import get_supabase_client
        from generator import normalize_markdown_fences
    except ModuleNotFoundError as exc:
        need = exc.name or "dependency"
        print(
            f'Missing Python module "{need}". Install ingest dependencies:\n'
            "  python3 -m pip install -r services/ingest/requirements.txt",
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
            .select("id, title, content")
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
            content_in = row.get("content") or ""
            if not isinstance(content_in, str):
                content_in = str(content_in)

            content_out = normalize_markdown_fences(content_in)
            if content_out == content_in:
                continue

            total_updated += 1
            if args.dry_run:
                preview = title_in[:72] + ("…" if len(title_in) > 72 else "")
                print(f"[dry-run] would update id={pid} title={preview!r}")
                continue

            client.from_("posts").update({"content": content_out}).eq("id", pid).execute()

        if len(rows) < page_size:
            break
        start += page_size

    mode = "dry-run" if args.dry_run else "applied"
    print(f"Done ({mode}): scanned={total_scanned}, rows_with_changes={total_updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
