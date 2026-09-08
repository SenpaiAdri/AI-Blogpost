"""Supabase persistence: tag upsert + post insert + post_tags linking."""

from typing import Dict, List

from infra.logger import get_logger
from safety.slugs import slugify_tag

logger = get_logger("ingest")


def save_post(client, post_data: dict) -> bool:
    """Save generated post to database."""
    try:
        tag_ids = []

        if post_data.get("tags"):
            for tag_name in post_data["tags"]:
                slug = slugify_tag(tag_name)

                tag_response = client.from_("tags").upsert(
                    {"name": tag_name, "slug": slug},
                    on_conflict="slug"
                ).execute()

                if tag_response.data:
                    tag_ids.append(tag_response.data[0]["id"])
                else:
                    existing = client.from_("tags").select("id").eq("slug", slug).execute()
                    if existing.data:
                        tag_ids.append(existing.data[0]["id"])

        post_data_clean = post_data.copy()
        post_data_clean.pop("tags", None)
        post_data_clean.pop("usage_metadata", None)

        post_response = client.from_("posts").insert(post_data_clean).execute()

        if not post_response.data:
            logger.error("Failed to insert post")
            return False

        post_id = post_response.data[0]["id"]

        if tag_ids:
            post_tags = [{"post_id": post_id, "tag_id": tid} for tid in tag_ids]
            client.from_("post_tags").insert(post_tags).execute()

        return True

    except Exception as e:
        logger.error(f"Error saving post: {e}")
        return False


def batch_save_posts(client, posts_data: List[Dict]) -> bool:
    """Save multiple posts in a single batch transaction."""
    try:
        tag_map = {}
        all_tags = set()

        for post_data in posts_data:
            if post_data.get("tags"):
                for tag_name in post_data["tags"]:
                    slug = slugify_tag(tag_name)
                    all_tags.add((tag_name, slug))

        if all_tags:
            for tag_name, slug in all_tags:
                tag_response = client.from_("tags").upsert(
                    {"name": tag_name, "slug": slug},
                    on_conflict="slug"
                ).execute()
                if tag_response.data:
                    tag_map[slug] = tag_response.data[0]["id"]

            for tag_name, slug in all_tags:
                if slug not in tag_map:
                    existing = client.from_("tags").select("id").eq("slug", slug).execute()
                    if existing.data:
                        tag_map[slug] = existing.data[0]["id"]

        posts_to_insert = []
        post_tags_list = []
        for post_data in posts_data:
            post_tags = []
            if post_data.get("tags"):
                for tag_name in post_data["tags"]:
                    slug = slugify_tag(tag_name)
                    if slug in tag_map:
                        post_tags.append(tag_map[slug])

            post_data_clean = post_data.copy()
            post_data_clean.pop("tags", None)
            post_data_clean.pop("usage_metadata", None)
            posts_to_insert.append(post_data_clean)
            post_tags_list.append(post_tags)

        response = client.from_("posts").insert(posts_to_insert).execute()

        if not response.data:
            logger.error("Batch insert failed - no data returned")
            return False

        post_tags_to_insert = []
        for i, post in enumerate(response.data):
            post_id = post["id"]
            tag_ids = post_tags_list[i] if i < len(post_tags_list) else []
            for tag_id in tag_ids:
                post_tags_to_insert.append({"post_id": post_id, "tag_id": tag_id})

        if post_tags_to_insert:
            client.from_("post_tags").insert(post_tags_to_insert).execute()

        return True

    except Exception as e:
        logger.error(f"Batch save error: {e}")
        return False
