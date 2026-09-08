"""Deprecated cover-image picker (no longer used for new posts).

Editorial decision: new posts ship with ``cover_image=None`` instead of
Unsplash hotlinks, to eliminate any image-licensing ambiguity and broken
hotlink risk. The ``cover_image`` column stays nullable so existing rows keep
working and the web app already handles ``None`` (no OG image).

Why removal beats Unsplash here, even though the Unsplash License permits
free commercial use without attribution:
- The curated IDs below carry no photographer credit or license receipt, so
  provenance cannot be audited later.
- Hotlinked CDN URLs can rot or change; a post with no cover degrades more
  gracefully than one with a broken/mismatched image.

``KEYWORD_MAP`` is still imported by ``generation.normalization`` for tag
fallback, so it stays. ``COVER_IMAGES`` and ``get_cover_image`` remain only
for backward compatibility (old imports, one-off scripts) and must not be
used for new posts.
"""

from typing import Optional


KEYWORD_MAP = {
    # Security (checked before broad matches like "apple")
    "ransomware": "security",
    "cybersecurity": "security",
    "vulnerability": "security",
    "breach": "security",
    "malware": "security",
    "phishing": "security",
    "zero-day": "security",
    "zeroday": "security",
    "encryption": "security",
    "firewall": "security",
    "exploit": "security",
    # Cloud & platforms
    "serverless": "cloud",
    "kubernetes": "devops",
    "docker": "devops",
    "devops": "devops",
    "terraform": "devops",
    "ansible": "devops",
    "jenkins": "devops",
    "ci/cd": "devops",
    "github actions": "devops",
    "nginx": "devops",
    "cloudflare": "cloud",
    "vercel": "cloud",
    "netlify": "cloud",
    "aws": "cloud",
    "azure": "cloud",
    "gcp": "cloud",
    "datacenter": "cloud",
    "data center": "cloud",
    "nvidia": "gpu",
    "gpu": "gpu",
    "cuda": "gpu",
    "llama": "llm",
    "gpt": "llm",
    "chatgpt": "llm",
    "claude": "llm",
    "gemini": "llm",
    "openai": "llm",
    "anthropic": "llm",
    "mistral": "llm",
    "model": "llm",
    "training": "ml",
    "machine learning": "ml",
    "deep learning": "ml",
    "neural": "ml",
    "robot": "robotics",
    "humanoid": "robotics",
    "automation": "robotics",
    "agent": "agent",
    "autonomous": "agent",
    "research": "research",
    "paper": "research",
    "benchmark": "research",
    "startup": "startup",
    "funding": "startup",
    "估值": "startup",
    "芯片": "hardware",
    "processor": "hardware",
    "hardware": "hardware",
    "tpu": "hardware",
    "quantum": "quantum",
}

COVER_IMAGES = {
    "security": [
        "https://images.unsplash.com/photo-1563986768609-322da13575f3",
        "https://images.unsplash.com/photo-1633265486064-086b219458ec",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b",
    ],
    "cloud": [
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa",
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8",
        "https://images.unsplash.com/photo-1451188502541-7bb938c7da26",
    ],
    "devops": [
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31",
        "https://images.unsplash.com/photo-1667372393119-3d4c48d07fc9",
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c",
    ],
    "llm": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485",
    ],
    "gpu": [
        "https://images.unsplash.com/photo-1555949963-ff9fe0c870eb",
    ],
    "ml": [
        "https://images.unsplash.com/photo-1555949963-aa79dcee981c",
    ],
    "robotics": [
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e",
    ],
    "agent": [
        "https://images.unsplash.com/photo-1535378917042-10a22c95931a",
    ],
    "research": [
        "https://images.unsplash.com/photo-1507413245164-6160d8298b31",
    ],
    "startup": [
        "https://images.unsplash.com/photo-1559136555-9303baea8ebd",
    ],
    "hardware": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475",
    ],
    "quantum": [
        "https://images.unsplash.com/photo-1635070041078-e363dbe005cb",
    ],
    "default": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485",
        "https://images.unsplash.com/photo-1535378917042-10a22c95931a",
    ],
}


def get_cover_image(title: str, content: str = "") -> Optional[str]:
    """Deprecated: always returns None so no new post gains a hotlinked cover.

    Kept for backward-compatible imports only. Do not use for new posts.
    """
    return None
