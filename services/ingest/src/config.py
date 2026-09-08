"""
Centralized configuration for AI Blogpost ingestion pipeline.

Single source of truth for all tunable parameters. Values can be
overridden via environment variables.

Other modules must import limits from here instead of redefining them:
  from config import MAX_TITLE_LENGTH, MAX_TAGS, DAILY_BUDGET_LIMIT, ...
"""

import os


def _bool_env(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


# ============================================================================
# DEDUPLICATION SETTINGS
# ============================================================================

DUPLICATE_CHECK_DAYS = int(os.getenv("DUPLICATE_CHECK_DAYS", "3"))

# Fuzzy duplicate threshold (0.0-1.0)
# Lower = more lenient, allows similar topics from multiple sources
# Higher = stricter, treats similar headlines as duplicates
FUZZY_TITLE_RATIO = float(os.getenv("FUZZY_TITLE_RATIO", "0.75"))

# Minimum characters for fuzzy comparison
FUZZY_MIN_CHARS = int(os.getenv("FUZZY_MIN_CHARS", "28"))

# Minimum words for fuzzy comparison
FUZZY_MIN_WORDS = int(os.getenv("FUZZY_MIN_WORDS", "4"))

# ============================================================================
# PIPELINE LIMITS
# ============================================================================

# Maximum candidate items to select per ingestion run
MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "20"))

# Maximum items to fetch from each RSS feed
FETCH_ITEMS_PER_FEED = int(os.getenv("FETCH_ITEMS_PER_FEED", "15"))

# Maximum articles per feed source (for diversity)
MAX_PER_SOURCE = int(os.getenv("MAX_PER_SOURCE", "3"))

# ============================================================================
# RSS FEED SETTINGS
# ============================================================================

# Maximum concurrent feed fetches
MAX_FEED_WORKERS = int(os.getenv("MAX_FEED_WORKERS", "10"))

# RSS fetch timeout in seconds
RSS_TIMEOUT_SECONDS = int(os.getenv("RSS_TIMEOUT_SECONDS", "25"))

# ============================================================================
# AI GENERATION SETTINGS
# ============================================================================

# OpenRouter-only chain: DeepSeek V4 Flash primary, GLM Flash fallback.
# Override via env without code changes.
OPENROUTER_PRIMARY_MODEL = (
    os.getenv("OPENROUTER_PRIMARY_MODEL")
    or os.getenv("OPENROUTER_MODEL")
    or os.getenv("DEFAULT_AI_MODEL")
    or "deepseek/deepseek-v4-flash-0731"
)
OPENROUTER_FALLBACK_MODEL = (
    os.getenv("OPENROUTER_FALLBACK_MODEL")
    or os.getenv("FALLBACK_AI_MODEL")
    or "z-ai/glm-5.3-flash"
)
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)

# Backward-compat aliases. Prefer OPENROUTER_PRIMARY_MODEL / FALLBACK above.
OPENROUTER_MODEL = OPENROUTER_PRIMARY_MODEL
DEFAULT_AI_MODEL = OPENROUTER_PRIMARY_MODEL
FALLBACK_AI_MODEL = OPENROUTER_FALLBACK_MODEL

# Token limits for content sent to AI (OpenRouter primary / fallback)
CONTENT_TOKEN_LIMIT_PRIMARY = int(os.getenv("CONTENT_TOKEN_LIMIT_PRIMARY", "8000"))
CONTENT_TOKEN_LIMIT_FALLBACK = int(os.getenv("CONTENT_TOKEN_LIMIT_FALLBACK", "8000"))

# Chars of source material passed to the model.
SOURCE_CHAR_LIMIT = int(os.getenv("SOURCE_CHAR_LIMIT", "8000"))

# Generation parameters
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4000"))

# ============================================================================
# IMAGE SETTINGS
# ============================================================================

VERIFY_INLINE_IMAGES = _bool_env("VERIFY_INLINE_IMAGES", "1")
IMAGE_URL_CHECK_TIMEOUT_SECONDS = float(os.getenv("IMAGE_URL_CHECK_TIMEOUT_SECONDS", "4"))
# Default to stripping inline markdown images: hotlinking publisher images
# without a license risks copyright infringement and hotlink blocking.
# Opt-out only: stripping stays ON unless explicitly disabled with
# STRIP_MARKDOWN_IMAGES=0 (also accepts false/no/off). An empty/unset value
# (e.g. unset GitHub secret expanding to "") still strips, so CI is safe.
STRIP_MARKDOWN_IMAGES = (
    os.getenv("STRIP_MARKDOWN_IMAGES", "1").strip().lower()
    not in ("0", "false", "no", "off")
)

# Comma-separated list of allowed domains for inline images (empty = all allowed)
ALLOW_INLINE_IMAGE_DOMAINS = {
    d.strip().lower()
    for d in os.getenv("ALLOW_INLINE_IMAGE_DOMAINS", "").split(",")
    if d.strip()
}

# ============================================================================
# RATE LIMITING
# ============================================================================

# Per-domain requests-per-second (overridable per domain via
# RATE_LIMIT_RPS_<DOMAIN>, e.g. RATE_LIMIT_RPS_OPENAI_COM=1.0).
RATE_LIMIT_RPS_DEFAULT = float(os.getenv("RATE_LIMIT_RPS_DEFAULT", "2.0"))

# Legacy knobs (kept for compat; rate_limit.py uses RPS above).
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# ============================================================================
# COST TRACKING & BUDGET
# ============================================================================

# Daily budget limit in USD (0 = unlimited)
DAILY_BUDGET_LIMIT = float(os.getenv("DAILY_BUDGET_LIMIT", "2.0"))

# Cost per 1M tokens (for estimation fallback)
COST_PER_MILLION_TOKENS = float(os.getenv("COST_PER_MILLION_TOKENS", "0.5"))

# ============================================================================
# CONTENT LIMITS (single source of truth — do not redefine elsewhere)
# ============================================================================

MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "200"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "50000"))
MAX_SLUG_LENGTH = int(os.getenv("MAX_SLUG_LENGTH", "100"))
MAX_EXCERPT_LENGTH = int(os.getenv("MAX_EXCERPT_LENGTH", "500"))
MIN_BLOG_CONTENT_CHARS = int(os.getenv("MIN_BLOG_CONTENT_CHARS", "400"))
MIN_TLDR_ITEMS = int(os.getenv("MIN_TLDR_ITEMS", "1"))
MAX_TLDR_ITEMS = int(os.getenv("MAX_TLDR_ITEMS", "5"))
MIN_TAGS = int(os.getenv("MIN_TAGS", "1"))
MAX_TAGS = int(os.getenv("MAX_TAGS", "5"))
MAX_TAG_LENGTH = int(os.getenv("MAX_TAG_LENGTH", "30"))
MAX_TLDR_LENGTH = int(os.getenv("MAX_TLDR_LENGTH", "200"))

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable verbose logging
VERBOSE_LOGGING = _bool_env("VERBOSE_LOGGING", "0")

# Enable fuzzy deduplication (disable for testing)
ENABLE_FUZZY_DEDUP = _bool_env("ENABLE_FUZZY_DEDUP", "1")
