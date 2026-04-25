"""
Centralized configuration for AI Blogpost ingestion pipeline.

All tunable parameters are defined here. Values can be overridden via environment variables.
"""

import os

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

# Primary AI model
DEFAULT_AI_MODEL = os.getenv("DEFAULT_AI_MODEL", "gemini-2.5-flash")

# Fallback AI model
FALLBACK_AI_MODEL = os.getenv("FALLBACK_AI_MODEL", "google/gemma-3-27b-it")

# OpenRouter settings
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Token limits for content sent to AI
CONTENT_TOKEN_LIMIT_GEMINI = int(os.getenv("CONTENT_TOKEN_LIMIT_GEMINI", "4000"))
CONTENT_TOKEN_LIMIT_OPENROUTER = int(os.getenv("CONTENT_TOKEN_LIMIT_OPENROUTER", "8000"))

# Generation parameters
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.7"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4000"))

# ============================================================================
# IMAGE SETTINGS
# ============================================================================

VERIFY_INLINE_IMAGES = os.getenv("VERIFY_INLINE_IMAGES", "1").strip().lower() in ("1", "true", "yes")
IMAGE_URL_CHECK_TIMEOUT_SECONDS = int(os.getenv("IMAGE_URL_CHECK_TIMEOUT_SECONDS", "4"))
STRIP_MARKDOWN_IMAGES = os.getenv("STRIP_MARKDOWN_IMAGES", "").strip().lower() in ("1", "true", "yes")

# Comma-separated list of allowed domains for inline images (empty = all allowed)
ALLOW_INLINE_IMAGE_DOMAINS = {
    d.strip().lower()
    for d in os.getenv("ALLOW_INLINE_IMAGE_DOMAINS", "").split(",")
    if d.strip()
}

# ============================================================================
# RATE LIMITING
# ============================================================================

# Global request delay (seconds) between requests to same host
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))

# Per-host rate limit (requests per WINDOW_SECONDS)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# ============================================================================
# COST TRACKING & BUDGET
# ============================================================================

# Daily budget limit in USD (0 = unlimited)
DAILY_BUDGET_LIMIT = float(os.getenv("DAILY_BUDGET_LIMIT", "0"))

# Cost per 1M tokens (for estimation)
COST_PER_MILLION_TOKENS = float(os.getenv("COST_PER_MILLION_TOKENS", "0.5"))

# ============================================================================
# CONTENT LIMITS
# ============================================================================

MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "200"))
MAX_EXCERPT_LENGTH = int(os.getenv("MAX_EXCERPT_LENGTH", "200"))
MAX_TLDR_ITEMS = int(os.getenv("MAX_TLDR_ITEMS", "5"))
MAX_TAGS = int(os.getenv("MAX_TAGS", "8"))

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable verbose logging
VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "0").strip().lower() in ("1", "true", "yes")

# Enable fuzzy deduplication (disable for testing)
ENABLE_FUZZY_DEDUP = os.getenv("ENABLE_FUZZY_DEDUP", "1").strip().lower() in ("1", "true", "yes")