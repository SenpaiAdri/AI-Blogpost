#!/usr/bin/env python3
"""Null out posts.cover_image on existing rows (covers removed by policy).

New posts are already written with cover_image=None. Use this one-off script
to apply the same policy to previously published rows that still carry
Unsplash hotlinks.

Loads services/ingest/.env. Requires SUPABASE_URL and SUPABASE_SERVICE_KEY (or
SUPABASE_SERVICE_ROLE_KEY).

  python services/ingest/scripts/backfill_remove_covers.py --dry-run
  python services/ingest/scripts/backfill_remove_covers.py
  python services/ingest/scripts/backfill_remove_covers.py --dry-run --limit 5

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
        from infra.database import get_supabase_client
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
    total_with_cover = 0
    total_updated = 0
    processed_cap = args.limit if args.limit and args.limit > 0 else None

    while True:
        if processed_cap is not None and total_scanned >= processed_cap:
            break

        end = start + page_size - 1
        response = (
            client.from_("posts")
            .select("id, title, cover_image")
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
            if not row.get("cover_image"):
                continue

            total_with_cover += 1
            pid = row["id"]
            title_preview = (row.get("title") or "")[:56]
            if args.dry_run:
                print(f"[dry-run] would null cover id={pid} title={title_preview!r}...")
                continue

            client.from_("posts").update({"cover_image": None}).eq("id", pid).execute()
            total_updated += 1

        if len(rows) < page_size:
            break
        start += page_size

    mode = "dry-run" if args.dry_run else "applied"
    print(
        f"Done ({mode}): scanned={total_scanned}, "
        f"posts_with_cover={total_with_cover}, rows_updated={total_updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
