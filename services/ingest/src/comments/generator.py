"""Selective generation: score a post, then comment only if worthy.

Chain mirrors generation/llm_client.py (OpenRouter primary -> fallback with
budget gates), but returns plain text / scores instead of blog JSON.
"""

import os
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

from comments.prompts import (
    COMMENT_SYSTEM_PROMPT,
    SCORE_SYSTEM_PROMPT,
    build_comment_prompt,
    build_score_prompt,
)
from config import (
    COMMENTS_FALLBACK_MODEL,
    COMMENTS_MAX_TOKENS,
    COMMENTS_MODEL,
    COMMENTS_SCORE_MAX_TOKENS,
    COMMENTS_TEMPERATURE,
    OPENROUTER_BASE_URL,
)
from generation.json_recovery import recover_json
from infra.logger import get_logger
from infra.metrics import cost_tracker, estimate_tokens

logger = get_logger("comments")

OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")


class InsufficientCredits(Exception):
    """OpenRouter key cannot fund the request (402: spent credits or key
    monthly limit). Retrying with the same key cannot help."""


def _is_insufficient_credits(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) == 402:
        return True
    lowered = str(exc).lower()
    return (
        "insufficient credits" in lowered
        or "can only afford" in lowered
        or ("402" in str(exc) and "credit" in lowered)
    )


def _chat(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    client: Any = None,
) -> Tuple[Optional[str], int, int]:
    """Single chat completion. Returns (text_or_None, input_tokens, output_tokens)."""
    if client is None:
        if not OPEN_ROUTER_API_KEY:
            return None, 0, 0
        client = OpenAI(api_key=OPEN_ROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        detail = str(e)[:500]
        if _is_insufficient_credits(e):
            logger.warning(f"    OpenRouter credits/key limit hit ({model}); aborting run")
            raise InsufficientCredits(detail)
        logger.warning(f"    Comment LLM error ({model}): {detail}")
        return None, 0, 0

    text = getattr(response.choices[0].message, "content", None) or ""
    if not text.strip():
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        hint = (
            "; model may need more reasoning headroom — consider raising COMMENTS_MAX_TOKENS"
            if finish_reason == "length"
            else ""
        )
        logger.warning(f"    Empty comment response (finish_reason={finish_reason}{hint})")
        return None, 0, 0

    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", None)
    output_tokens = getattr(usage, "completion_tokens", None)
    if input_tokens is None:
        input_tokens = estimate_tokens(user_prompt)
    if output_tokens is None:
        output_tokens = estimate_tokens(text)
    cost_tracker.track_request(model, input_tokens, output_tokens)
    return text, input_tokens, output_tokens


def _parse_score(text: str) -> Tuple[float, str]:
    """Extract (score 0-10, reason) from a scoring response; 0.0 on failure."""
    try:
        data = recover_json(text)
        score = float(data.get("score", 0.0))
        reason = str(data.get("reason", "")).strip()[:300]
        return max(0.0, min(10.0, score)), reason
    except Exception:
        logger.warning("    Failed to parse comment score; treating as 0")
        return 0.0, "score_parse_failed"


def score_post(
    post: Dict[str, Any],
    model: Optional[str] = None,
    client: Any = None,
) -> Tuple[float, str, Optional[str]]:
    """Score worthiness 0-10 via primary, then fallback. Returns (score, reason, model_used)."""
    user_prompt = build_score_prompt(post)
    last_reason = "scoring_failed"
    for candidate in (model or COMMENTS_MODEL, COMMENTS_FALLBACK_MODEL):
        if candidate == COMMENTS_FALLBACK_MODEL and (model or COMMENTS_MODEL) == COMMENTS_FALLBACK_MODEL:
            break  # primary IS the fallback; don't try twice
        if not cost_tracker.should_continue():
            logger.warning("    Budget exhausted, skipping comment scoring")
            return 0.0, "budget_exhausted", None
        logger.info(f"    Scoring post for comment ({candidate})...")
        text, _, _ = _chat(
            candidate, SCORE_SYSTEM_PROMPT, user_prompt,
            COMMENTS_TEMPERATURE, COMMENTS_SCORE_MAX_TOKENS, client,
        )
        if text is None:
            continue
        score, reason = _parse_score(text)
        if reason == "score_parse_failed":
            last_reason = reason
            continue
        return score, reason, candidate
    return 0.0, last_reason, None


def generate_comment_for_post(
    post: Dict[str, Any],
    model: Optional[str] = None,
    client: Any = None,
) -> Optional[Dict[str, Any]]:
    """Generate one comment body via primary, then fallback. Returns dict or None."""
    user_prompt = build_comment_prompt(post)
    for candidate in (model or COMMENTS_MODEL, COMMENTS_FALLBACK_MODEL):
        if candidate == COMMENTS_FALLBACK_MODEL and (model or COMMENTS_MODEL) == COMMENTS_FALLBACK_MODEL:
            break
        if not cost_tracker.should_continue():
            logger.warning("    Budget exhausted, skipping comment generation")
            return None
        logger.info(f"    Generating comment ({candidate})...")
        text, input_tokens, output_tokens = _chat(
            candidate, COMMENT_SYSTEM_PROMPT, user_prompt,
            COMMENTS_TEMPERATURE, COMMENTS_MAX_TOKENS, client,
        )
        if text is None:
            continue
        body = text.strip()
        if len(body) < 20:
            logger.warning("    Comment too short, trying fallback" if candidate != COMMENTS_FALLBACK_MODEL else "    Comment too short")
            continue
        if "![" in body:
            logger.warning("    Comment contains markdown image, trying fallback" if candidate != COMMENTS_FALLBACK_MODEL else "    Comment contains markdown image")
            continue
        logger.info("    ✓ Comment generated")
        return {
            "body": body,
            "ai_model": candidate,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    logger.warning("    Comment generation failed, no more providers to try")
    return None
