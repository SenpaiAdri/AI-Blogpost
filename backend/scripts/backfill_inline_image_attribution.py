#!/usr/bin/env python3
"""Apply inline image attribution (or strip) to existing posts.content in Supabase.

Uses the same logic as generator.process_inline_images: after each markdown image
`![alt](url)`, inserts a credit line linking to the post's primary source article,
unless one is already present or the article URL already appears nearby.

Respects STRIP_MARKDOWN_IMAGES from the environment (same as ingest): when set to
1/true/yes, replaces images with a text link to the original article instead.

Loads backend/.env. Requires SUPABASE_URL and SUPABASE_SERVICE_KEY (or
SUPABASE_SERVICE_ROLE_KEY).

  python backend/scripts/backfill_inline_image_attribution.py --dry-run
  python backend/scripts/backfill_inline_image_attribution.py
  python backend/scripts/backfill_inline_image_attribution.py --dry-run --limit 3

Requires backend dependencies: pip install -r backend/requirements.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Tuple


def _primary_source(source_url: Any) -> Tuple[str, str]:
    """Return (name, url) from posts.source_url JSON."""
    if not source_url:
        return ("", "")
    data = source_url
    if isinstance(data, str):
        data = data.strip()
        if not data:
            return ("", "")
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return ("", "")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            name = str(first.get("name") or "").strip()
            url = str(first.get("url") or "").strip()
            return (name, url)
    return ("", "")


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.normpath(os.path.join(root, "..", "src"))
    sys.path.insert(0, src)

    try:
        from database import get_supabase_client
        from generator import _MARKDOWN_IMAGE, process_inline_images
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
    total_with_images = 0
    total_updated = 0
    processed_cap = args.limit if args.limit and args.limit > 0 else None

    while True:
        if processed_cap is not None and total_scanned >= processed_cap:
            break

        end = start + page_size - 1
        response = (
            client.from_("posts")
            .select("id, title, content, source_url")
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
            content_in = row.get("content") or ""
            if not _MARKDOWN_IMAGE.search(content_in):
                continue

            total_with_images += 1
            name, url = _primary_source(row.get("source_url"))
            content_out = process_inline_images(content_in, name, url)

            if content_out == content_in:
                continue

            total_updated += 1
            title_preview = (row.get("title") or "")[:56]
            if args.dry_run:
                print(f"[dry-run] would update id={pid} title={title_preview!r}...")
                continue

            client.from_("posts").update({"content": content_out}).eq("id", pid).execute()

        if len(rows) < page_size:
            break
        start += page_size

    mode = "dry-run" if args.dry_run else "applied"
    print(
        f"Done ({mode}): scanned={total_scanned}, "
        f"posts_with_markdown_images={total_with_images}, rows_updated={total_updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
