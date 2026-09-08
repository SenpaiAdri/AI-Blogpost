"""OpenRouter LLM client: primary -> fallback chain with budget gates."""

import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config import (
    AI_MAX_TOKENS,
    AI_TEMPERATURE,
    OPENROUTER_BASE_URL,
    OPENROUTER_FALLBACK_MODEL,
    OPENROUTER_PRIMARY_MODEL,
    SOURCE_CHAR_LIMIT,
)
from generation.json_recovery import recover_json
from generation.normalization import finalize_result
from generation.prompts import SYSTEM_PROMPT, build_user_prompt
from infra.logger import get_logger
from infra.metrics import cost_tracker, estimate_tokens

logger = get_logger("generator")

OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")

# Backward-compat alias (primary). Prefer OPENROUTER_PRIMARY_MODEL.
OPENROUTER_MODEL = OPENROUTER_PRIMARY_MODEL


def generate_with_openrouter(
    topic: str,
    article_content: str,
    source_name: str,
    source_url: str,
    active_topics: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Generate blog post using OpenRouter with the given model (default: primary)."""
    if not OPENROUTER_API_KEY:
        return None

    model = model or OPENROUTER_PRIMARY_MODEL

    try:
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )

        user_prompt = build_user_prompt(
            topic, article_content, source_name, source_url,
            source_char_limit=SOURCE_CHAR_LIMIT, active_topics=active_topics,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=AI_TEMPERATURE,
            max_tokens=AI_MAX_TOKENS,
        )

        text = (getattr(response.choices[0].message, "content", None) or "")
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        logger.debug(f"    Raw response length: {len(text)}")
        if not text:
            # Provider returned no content: content-filter refusal, empty
            # completion, or upstream hiccup. Never len()/parse None — say
            # what happened so CI logs stay diagnosable.
            refusal = getattr(response.choices[0].message, "refusal", None)
            refusal_note = f", refusal={str(refusal)[:300]!r}" if refusal else ""
            logger.warning(
                "    Empty model response (finish_reason=%s%s); "
                "possible content filter or provider hiccup",
                finish_reason,
                refusal_note,
            )
            return None

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None)
        output_tokens = getattr(usage, "completion_tokens", None)
        if input_tokens is None:
            input_tokens = estimate_tokens(article_content[:SOURCE_CHAR_LIMIT])
        if output_tokens is None:
            output_tokens = estimate_tokens(text)
        cost_tracker.track_request(model, input_tokens, output_tokens)

        result = recover_json(text)
        if not result:
            logger.warning("    Failed to parse JSON response")
            logger.warning("    Response preview (first 500 chars): %r", text[:500])
            return None

        return finalize_result(result, model, topic, source_name, source_url, input_tokens, output_tokens)

    except Exception as e:
        logger.warning(f"    OpenRouter error: {e}")
        return None


def generate_blog_post(
    topic: str,
    article_content: str,
    source_name: str,
    source_url: str,
    active_topics: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Generate blog post via OpenRouter-only chain: primary, then fallback model."""
    logger.info(f"    Trying OpenRouter primary ({OPENROUTER_PRIMARY_MODEL})...")

    if not cost_tracker.should_continue():
        logger.warning("    Budget exhausted, skipping AI generation")
        return None

    result = generate_with_openrouter(
        topic, article_content, source_name, source_url,
        active_topics=active_topics, model=OPENROUTER_PRIMARY_MODEL,
    )
    if result:
        logger.info("    ✓ OpenRouter primary succeeded")
        return result

    logger.info(f"    Trying OpenRouter fallback ({OPENROUTER_FALLBACK_MODEL})...")

    if not cost_tracker.should_continue():
        logger.warning("    Budget exhausted, skipping fallback")
        return None

    result = generate_with_openrouter(
        topic, article_content, source_name, source_url,
        active_topics=active_topics, model=OPENROUTER_FALLBACK_MODEL,
    )
    if result:
        logger.info("    ✓ OpenRouter fallback succeeded")
        return result

    logger.warning("    AI generation failed, no more providers to try")
    return None
