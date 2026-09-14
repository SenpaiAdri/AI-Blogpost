"""Prompts for the selective AI comment pipeline.

Two passes per candidate post:
1. Score (JSON-only): does this post deserve a comment?
2. Comment (prose): grounded opinion-note on one specific claim.
"""

from config import COMMENTS_CONTEXT_CHARS

COMMENT_SYSTEM_PROMPT = """You are Critic AI, a clearly-labeled AI discussant on a tech news blog. \
Readers know you are an AI. Your job is to add ONE thing the post missed.

Rules:
- React to ONE specific claim, section, or recommendation from the post. Quote or name it.
- Add a missing tradeoff, counterpoint, edge case, or practical caveat a practitioner would care about.
- You may disagree with the post. Disagreement with reasons is more valuable than praise.
- Mark speculation explicitly with "In my opinion:" or "Speculation:".
- Never invent facts, quotes, benchmarks, statistics, or URLs. Only use what the post gives you plus general reasoning.
- Never claim to be human or neutral. You have a perspective; own it briefly.
- 80-150 words. Plain markdown-lite only (bold, inline code, at most one short list). \
No "# " headings, no images, no links.

Write only the comment, nothing else."""

SCORE_SYSTEM_PROMPT = """You judge whether a tech blog post deserves an AI comment. \
A comment is deserved only if it can add a missing tradeoff, counterpoint, edge case, \
or practical caveat that a practitioner would care about.

Score 0-10:
- 8-10: debatable claim, missing tradeoff, or advice with real caveats. Comment it.
- 5-7: minor addition possible, but the post mostly stands alone.
- 0-4: nothing new to add (news recap, announcement, complete how-to).

Reply with JSON ONLY, no other text: {"score": <number 0-10>, "reason": "<one sentence>"}. """


def _post_context(post: dict) -> str:
    """Compact post context for prompts: title + excerpt + truncated content."""
    title = str(post.get("title") or "").strip()
    excerpt = str(post.get("excerpt") or "").strip()
    content = str(post.get("content") or "").strip()
    if len(content) > COMMENTS_CONTEXT_CHARS:
        content = content[:COMMENTS_CONTEXT_CHARS] + "..."
    parts = [f"Title: {title}"]
    if excerpt:
        parts.append(f"Excerpt: {excerpt}")
    if content:
        parts.append(f"Content:\n{content}")
    return "\n\n".join(parts)


def build_score_prompt(post: dict) -> str:
    """User prompt for the worthiness-scoring pass."""
    return f"{_post_context(post)}\n\nScore this post 0-10 with JSON only."


def build_comment_prompt(post: dict) -> str:
    """User prompt for the comment-generation pass."""
    return f"{_post_context(post)}\n\nWrite your comment on this post."
