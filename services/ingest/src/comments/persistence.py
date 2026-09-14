"""Supabase writes for AI comments (validated insert + dry-run support)."""

from typing import Any, Optional

from config import COMMENTS_AUTHOR_NAME
from infra.logger import get_logger
from models import CommentInsertModel

logger = get_logger("comments")


def save_comment(
    client: Any,
    post_id: str,
    body: str,
    ai_model: Optional[str] = None,
    author_name: str = COMMENTS_AUTHOR_NAME,
    status: str = "approved",
    dry_run: bool = False,
) -> bool:
    """Validate and insert one AI comment. Returns True on success (or dry-run)."""
    try:
        validated = CommentInsertModel(
            post_id=post_id,
            author_type="ai",
            author_name=author_name,
            body=body,
            ai_model=ai_model,
            status=status,
        )
    except Exception as e:
        logger.warning(f"Comment validation failed for post {post_id}: {e}")
        return False

    if dry_run:
        logger.info(f"[dry-run] Would comment on post {post_id} ({len(body)} chars)")
        return True

    try:
        payload = validated.model_dump(exclude_none=True)
        response = client.from_("comments").insert(payload).execute()
        if not response.data:
            logger.error(f"Failed to insert comment for post {post_id}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error saving comment for post {post_id}: {e}")
        return False
