"""Keyword vocabularies for the tiered relevance filter.

Scope: AI + software engineering (+ security only with an AI/dev angle).

- CORE_* alone passes: AI terms and SWE terms are sufficient relevance.
- ADJACENT_* requires a CORE co-signal in the same title+snippet: big-tech
  names, security/infra/hardware, enterprise/SaaS, quantum/robotics only
  count when paired with AI or SWE (e.g. "Apple AI coding assistant" passes,
  "Apple Maps towns" fails; "prompt-injection flaw in LangChain" passes,
  "Windows Patch Tuesday" fails).
"""

import re

CORE_AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural network", "neural networks", "neural",
    "llm", "large language model", "small language model", "slm",
    "generative ai", "generative", "stable diffusion", "diffusion model",
    "multimodal", "agentic", "ai agent", "ai agents", "ai assistant",
    "reasoning model", "foundation model", "frontier model",
    "gpt", "chatgpt", "openai", "anthropic", "claude", "gemini",
    "deepmind", "llama", "gemma", "mistral", "deepseek",
    "hugging face", "cohere", "perplexity", "midjourney", "runway",
    "stability ai", "grok", "qwen", "kimi", "phi",
    "transformer", "embeddings", "embedding model",
    "rag", "retrieval-augmented", "retrieval augmented",
    "vector database", "vector db",
    "prompt engineering", "fine-tuning", "finetuning", "finetune", "rlhf",
    "pytorch", "tensorflow", "jax", "langchain", "llamaindex", "ollama",
    "copilot", "chatbot", "voice agent", "coding agent",
    "text-to-image", "text to image", "image generation", "video generation",
    "edge ai", "physical ai", "artificial general intelligence", "agi",
]

CORE_SWE_KEYWORDS = [
    "developer", "developers", "programmer", "programming", "coding",
    "software development", "software engineer", "software engineering",
    "software architecture", "open source", "github", "gitlab", "git",
    "pull request", "code review", "devtools", "developer tools",
    "programming language", "api", "sdk", "framework", "library",
    "ide", "vscode", "vs code",
    "python", "javascript", "typescript", "rust", "golang", "kotlin",
    "swift", "ruby", "php", "scala", "haskell", "elixir", "dart",
    "npm", "node.js", "nodejs", "deno", "bun",
    "react", "react.js", "react native", "next.js", "nextjs",
    "vue", "vue.js", "angular", "svelte", "vite", "webpack",
    "flutter", "tailwind",
    "linux", "kernel", "ubuntu",
    "database", "postgresql", "postgres", "mysql", "sqlite",
    "redis", "mongodb", "elasticsearch", "kafka", "rabbitmq",
    "docker", "kubernetes", "terraform", "pulumi", "ansible", "devops",
    "ci/cd", "github actions", "gitlab ci", "jenkins", "circleci",
    "serverless", "wasm", "webassembly",
    "refactor", "refactoring", "debugging", "unit test", "integration test",
]

CORE_KEYWORDS = CORE_AI_KEYWORDS + CORE_SWE_KEYWORDS

ADJACENT_SECURITY_KEYWORDS = [
    "security", "cybersecurity", "infosec",
    "ransomware", "vulnerability", "breach", "malware",
    "patch", "encryption", "privacy", "phishing",
    "zero-day", "zeroday", "deepfake", "supply chain attack", "pqc",
    "identity", "oauth", "sso", "mfa",
    "infostealer", "data breach", "threat", "exploit", "cve",
    "firewall", "pentest", "penetration test",
]

ADJACENT_INFRA_KEYWORDS = [
    "cloud", "server", "datacenter", "data center", "infrastructure",
    "aws", "azure", "gcp", "google cloud",
    "cdn", "edge computing",
    "vercel", "netlify", "cloudflare", "fastly", "akamai",
    "nginx", "apache", "caddy", "haproxy", "traefik",
]

ADJACENT_HARDWARE_KEYWORDS = [
    "semiconductor", "processor", "chip", "intel", "amd",
    "apple silicon", "nvidia", "gpu", "cuda", "tpu", "npu", "asic",
    "hardware",
]

ADJACENT_BIGTECH_KEYWORDS = [
    "microsoft", "apple", "google", "meta", "amazon", "samsung", "alphabet",
]

ADJACENT_BUSINESS_KEYWORDS = [
    "enterprise", "saas", "startup", "startups", "funding",
    "venture capital", "series a", "series b", "ipo", "earnings",
]

ADJACENT_EMERGING_KEYWORDS = [
    "quantum", "qubit", "qpu", "quantum computing", "quantum computer",
    "robotics", "robot", "humanoid", "drone",
]

ADJACENT_KEYWORDS = (
    ADJACENT_SECURITY_KEYWORDS
    + ADJACENT_INFRA_KEYWORDS
    + ADJACENT_HARDWARE_KEYWORDS
    + ADJACENT_BIGTECH_KEYWORDS
    + ADJACENT_BUSINESS_KEYWORDS
    + ADJACENT_EMERGING_KEYWORDS
)

# Kept for backward compatibility (combined vocabulary). Matching logic in
# relevance.py is tiered: CORE alone passes, ADJACENT requires a CORE co-signal.
TECH_KEYWORDS = CORE_KEYWORDS + ADJACENT_KEYWORDS


def _compile_keyword_patterns(keywords) -> list:
    return [
        re.compile(r"\b" + re.escape(kw.strip().lower()) + r"\b")
        for kw in keywords
        if kw.strip()
    ]


_CORE_KEYWORD_PATTERNS = _compile_keyword_patterns(CORE_KEYWORDS)

_ADJACENT_KEYWORD_PATTERNS = _compile_keyword_patterns(ADJACENT_KEYWORDS)

# Legacy combined patterns (kept for backward compat / debugging).
_TECH_KEYWORD_PATTERNS = _compile_keyword_patterns(TECH_KEYWORDS)
