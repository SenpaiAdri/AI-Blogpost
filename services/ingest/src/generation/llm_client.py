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

        text = response.choices[0].message.content
        logger.debug(f"    Raw response length: {len(text)}")

        input_tokens = response.usage.prompt_tokens if hasattr(response, 'usage') else estimate_tokens(article_content[:SOURCE_CHAR_LIMIT])
        output_tokens = response.usage.completion_tokens if hasattr(response, 'usage') else estimate_tokens(text)
        cost_tracker.track_request(model, input_tokens, output_tokens)

        result = recover_json(text)
        if not result:
            logger.warning("    Failed to parse JSON response")
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
