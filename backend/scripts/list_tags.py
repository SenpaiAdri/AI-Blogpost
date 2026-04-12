#!/usr/bin/env python3
"""List every tag in Supabase with optional published post counts.

Loads backend/.env (same as the ingest pipeline). Requires service role access.

Requires backend Python deps (same as ingest), e.g. from repo root:

  python3 -m pip install -r backend/requirements.txt

Usage:
  python backend/scripts/list_tags.py
  python backend/scripts/list_tags.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.normpath(os.path.join(root, "..", "src"))
    sys.path.insert(0, src)

    try:
        from database import get_supabase_client
    except ModuleNotFoundError as exc:
        need = exc.name or "dependency"
        print(
            f'Missing Python module "{need}". Install backend dependencies first:\n'
            "  python3 -m pip install -r backend/requirements.txt\n"
            "(from the repository root; use the same venv you use for ingest if any.)\n"
            'If python3 -m pip fails with "No module named pip", install pip, e.g.\n'
            "  sudo pacman -S python-pip    # CachyOS / Arch\n"
            "  python3 -m ensurepip --upgrade   # built-in bootstrap, if available",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description="List all tags from the database.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON (id, name, slug, post_count).",
    )
    args = parser.parse_args()

    client = get_supabase_client()

    tags_res = client.from_("tags").select("id, name, slug").order("name").execute()
    if tags_res.data is None:
        print("No tags returned.", file=sys.stderr)
        return 1

    tags = tags_res.data

    counts: Counter[str] = Counter()
    posts_res = (
        client.from_("posts").select("id").eq("is_published", True).execute()
    )
    published_ids = {row["id"] for row in (posts_res.data or [])}

    links_res = client.from_("post_tags").select("tag_id, post_id").execute()
    if links_res.data:
        for row in links_res.data:
            if row.get("post_id") not in published_ids:
                continue
            tid = row.get("tag_id")
            if tid is not None:
                counts[str(tid)] += 1

    rows = []
    for t in tags:
        tid = str(t["id"])
        rows.append(
            {
                "id": t["id"],
                "name": t["name"],
                "slug": t["slug"],
                "post_count": counts.get(tid, 0),
            }
        )

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"Tags in database: {len(rows)}\n")
    w = max(len(str(r["post_count"])) for r in rows) if rows else 1
    for r in rows:
        c = r["post_count"]
        print(f"{str(c).rjust(w)}  {r['name']}  ({r['slug']})  id={r['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
