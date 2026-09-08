"""AI generation stage: prompts -> LLM -> normalize."""

from generation.cover import COVER_IMAGES, KEYWORD_MAP, get_cover_image  # noqa: F401
from generation.images import _MARKDOWN_IMAGE, process_inline_images  # noqa: F401
from generation.json_recovery import recover_json  # noqa: F401
from generation.llm_client import (  # noqa: F401
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_FALLBACK_MODEL,
    OPENROUTER_MODEL,
    OPENROUTER_PRIMARY_MODEL,
    generate_blog_post,
    generate_with_openrouter,
)
from generation.markdown import (  # noqa: F401
    balance_markdown_fences,
    fix_code_blocks,
    fix_tables,
    normalize_markdown_fences,
    repair_leaked_markdown_fences,
    sanitize_ai_content,
)
from generation.normalization import (  # noqa: F401
    _NORMALIZATION_FALLBACK_BY_MODEL,
    _NORMALIZATION_FALLBACK_COUNTS,
    finalize_result,
    get_normalization_fallback_counts,
    get_normalization_fallbacks_by_model,
    validate_and_normalize_result,
)
from generation.prompts import (  # noqa: F401
    ARTICLE_FORMATS,
    SYSTEM_PROMPT,
    build_topic_guidance_prompt_section,
    build_user_prompt,
    pick_article_shape,
)

__all__ = [
    "SYSTEM_PROMPT",
    "OPENROUTER_PRIMARY_MODEL",
    "OPENROUTER_FALLBACK_MODEL",
    "OPENROUTER_MODEL",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_API_KEY",
    "generate_blog_post",
    "generate_with_openrouter",
    "recover_json",
    "fix_tables",
    "normalize_markdown_fences",
    "process_inline_images",
    "finalize_result",
    "validate_and_normalize_result",
    "build_user_prompt",
    "build_topic_guidance_prompt_section",
    "pick_article_shape",
    "ARTICLE_FORMATS",
    "get_cover_image",
]
