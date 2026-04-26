import os
import json
import re
import html
import threading
import requests
import google.generativeai as genai
from openai import OpenAI
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
from urllib.parse import urlparse

from logger import get_logger
from metrics import cost_tracker, estimate_tokens, register_summary_provider

logger = get_logger("generator")

_NORMALIZATION_FALLBACK_COUNTS: Dict[str, int] = {}
_NORMALIZATION_FALLBACK_BY_MODEL: Dict[str, Dict[str, int]] = {}
_NORMALIZATION_METRICS_LOCK = threading.Lock()
_IMAGE_URL_CHECK_CACHE: Dict[str, bool] = {}
_IMAGE_URL_CHECK_TIMEOUT_SECONDS = float(os.getenv("IMAGE_URL_CHECK_TIMEOUT_SECONDS", "4"))
_VERIFY_INLINE_IMAGES = os.getenv("VERIFY_INLINE_IMAGES", "1").strip().lower() in (
    "1",
    "true",
    "yes",
)
_INLINE_IMAGE_ALLOWED_DOMAINS = {
    d.strip().lower()
    for d in os.getenv("ALLOW_INLINE_IMAGE_DOMAINS", "").split(",")
    if d.strip()
}

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")

# If true, replace ![alt](url) with a text link to the article (no hotlinked images).
_STRIP_MARKDOWN_IMAGES = os.getenv("STRIP_MARKDOWN_IMAGES", "").strip().lower() in (
    "1",
    "true",
    "yes",
)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

GEMINI_MODEL = "gemini-2.5-flash"
OPENROUTER_MODEL = "google/gemma-3-27b-it"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are an expert tech blogger for a site called "AI Blogpost".
Your task is to write a high-quality, engaging article for developers and IT readers based on a current tech news story.

Scope: Cover the full technology landscape when the source material supports it — including AI/ML, security, cloud and infrastructure, developer tools, platforms (e.g. browsers, mobile, web), hardware/chips, and enterprise/SaaS — not only artificial intelligence.

Audience fit:
- Focus on the technology angle. If the story is mainly politics, crime, culture, or general business, cover only the concrete technology relevance and avoid stretching it into developer analysis.
- Do not imply a story matters to developers or IT teams unless the source material supports that connection.

Output Format: JSON only
The output must be a valid JSON object with the following schema:
{
  "title": "Catchy and descriptive title",
  "slug": "kebab-case-slug-for-url",
  "tldr": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
  "content": "Full markdown content...",
  "excerpt": "Short teaser sentence (max 200 chars)",
  "tags": ["Tag1", "Tag2", "Tag3"]
}
Output contract:
- Return ONLY JSON. No prose before or after the JSON object.
- Use EXACTLY these keys: title, slug, tldr, content, excerpt, tags.
- Do not add source_url, cover_image, ai_model, or any extra keys; those are injected server-side.
- If evidence in source material is limited, avoid guessing. State uncertainty directly in content.
- Every concrete claim should be inferable from the provided source material.

Quality and accuracy:
- Ground claims in the provided source material; do not invent quotes, statistics, or product details.
- If the source is thin or unclear, say what is confirmed vs uncertain and what readers should watch for next.
- Prefer concrete implications for engineers, operators, or decision-makers over generic hype.
- If the source material is thin, keep the post concise (roughly 400-700 words) instead of padding with speculation.

Perspective & Analysis:
- Use this structure in content when possible: a brief opening paragraph, `## What Happened`, `## Why It Matters`, and `## What To Watch`.
- After summarizing WHAT happened, include a "Why It Matters" section that explains the implications
- Give readers your take on WHY this matters — not as opinion, but as analysis grounded in the facts presented
- Consider: What does this mean for developers? For enterprises? For the industry?
- If the source presents competing viewpoints, acknowledge them briefly
- NEVER invent a perspective — if the source doesn't give enough context to analyze, focus on the facts and say what readers should watch for
- Keep analysis grounded in evidence from the source material

Tags:
- Use 3-5 specific tags that reflect the real topic.
- Prefer this taxonomy when it fits: AI, Security, Cloud, DevOps, Developer Tools, Hardware, Policy, Data Centers, Quantum, Robotics, Open Source, Platforms, Enterprise.
- Do not return only "Tech News"; use "Tech News" only alongside more specific tags if absolutely necessary.

Guidelines:
- Content should be in Markdown format with proper headings (## Heading)
- Use proper markdown code fences: ```python for code blocks, NOT "python" on its own line
- Every fenced code block MUST end with a line containing only ``` (three backticks) before any following prose, headings, lists, tables, or images — never run prose or markdown inside an unclosed fence
- Use standard markdown tables with proper header row and separator row (|---|---|)
- Use actual characters in every JSON string (title, tldr, excerpt, tags, content). NEVER use HTML entities like &amp; &lt; &gt; &#x27; &#39; &quot; — use straight quotes and apostrophes instead
- Do NOT repeat the title in the content
- Do NOT include leading # in content - use ## for main sections
- No introductory text, just the JSON object
- Make the content informative and useful for developers
- Use exactly 3 TLDR bullets, each concise (max ~140 chars)
- Excerpt must be one complete sentence, max 180 characters, with no trailing ellipsis unless the source itself contains one.
- Target content length: ~700-1200 words when source material is rich; ~400-700 words when source material is thin.

Images (copyright and hotlinking):
- Do NOT invent, guess, or reconstruct image URLs. Only use `![description](url)` if that exact image URL appears in the Source Material.
- If the story references a photo but no URL is in the source text, describe it in prose and link readers to the original article — do not embed an image.
- When you do embed an image from the source, put the markdown image on its own line, then immediately add: `*Photo/source: [use the publisher name from Source](article URL from context).*` using the same article URL as in source_url, not the bare image CDN alone.
- When unsure about rights or the URL is not verbatim in the source, omit the image and link to the original article instead."""

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


def get_cover_image(title: str, content: str = "") -> str:
    """Generate a category-based cover image URL."""
    text = (title + " " + (content[:500] if content else "")).lower()
    
    for keyword, category in KEYWORD_MAP.items():
        if keyword in text and category in COVER_IMAGES:
            images = COVER_IMAGES[category]
            index = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(images)
            return images[index]
    
    images = COVER_IMAGES["default"]
    index = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(images)
    return images[index]


def recover_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to recover valid JSON from malformed AI response."""
    text = text.strip()
    
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\w*\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'```$', '', text)
    text = text.replace("```", "")
    
    text = re.sub(r'^Here is the JSON:.*?^\{', '{', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'^Here is the.*?:.*?^\{', '{', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'^\{.*', lambda m: m.group(0), text, flags=re.MULTILINE)
    
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
    
    text = re.sub(r',\s*\]', ']', text)
    text = re.sub(r',\s*\}', '}', text)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    try:
        text = "{" + text.split("{", 1)[1]
        text = text.rsplit("}", 1)[0] + "}"
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        pass
    
    return None


def fix_code_blocks(content: str) -> str:
    """Fix malformed code blocks in markdown."""
    content = re.sub(r'\n(python)\n', r'\n```python\n', content)
    content = re.sub(r'\n(javascript)\n', r'\n```javascript\n', content)
    content = re.sub(r'\n(js)\n', r'\n```javascript\n', content)
    content = re.sub(r'\n(typescript)\n', r'\n```typescript\n', content)
    content = re.sub(r'\n(ts)\n', r'\n```typescript\n', content)
    content = re.sub(r'\n(bash)\n', r'\n```bash\n', content)
    content = re.sub(r'\n(shell)\n', r'\n```bash\n', content)
    content = re.sub(r'\n(json)\n', r'\n```json\n', content)
    content = re.sub(r'\n(sql)\n', r'\n```sql\n', content)
    content = re.sub(r'\n(html)\n', r'\n```html\n', content)
    content = re.sub(r'\n(css)\n', r'\n```css\n', content)
    content = re.sub(r'\n(java)\n', r'\n```java\n', content)
    content = re.sub(r'\n(c\+\+)\n', r'\n```cpp\n', content)
    content = re.sub(r'\n(cpp)\n', r'\n```cpp\n', content)
    content = re.sub(r'\n(rust)\n', r'\n```rust\n', content)
    content = re.sub(r'\n(go)\n', r'\n```go\n', content)
    content = re.sub(r'\n(golang)\n', r'\n```go\n', content)
    
    content = re.sub(r'\n```python\n\n', '\n```python\n', content)
    content = re.sub(r'\n```javascript\n\n', '\n```javascript\n', content)
    content = re.sub(r'\n```bash\n\n', '\n```bash\n', content)
    
    return content


_FENCE_LINE = re.compile(r"^\s*`{3}")
# Markdown bold word (not Python `x ** 2` with a digit right after **)
_MD_BOLD_WORD = re.compile(r"\*\*[A-Za-z_][^*\n]*\*\*")


def _line_signals_markdown_outside_fence(line: str) -> bool:
    """True when this line is almost certainly prose/markdown, not code."""
    s = line.strip()
    if s.startswith("!["):
        return True
    if _MD_BOLD_WORD.search(line):
        return True
    return False


def repair_leaked_markdown_fences(content: str) -> str:
    """Close a ``` fence before prose that was left inside a code block.

    Models often open ```python, paste real code, then continue the article without
    closing the fence and put a single ``` at the very end. That parses as one giant
    code block (headings and images stay literal). We insert an early closing fence
    before obvious markdown (images, **bold**), then drop a stray trailing ``` that
    used to close the oversized block.
    """
    if not content or "```" not in content:
        return content

    lines = content.split("\n")
    out: List[str] = []
    in_fence = False
    inserted_mid_close = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if _FENCE_LINE.match(line):
            rest = stripped[3:].strip() if len(stripped) >= 3 else ""
            if in_fence:
                in_fence = False
                out.append(line)
                i += 1
                continue
            in_fence = True
            out.append(line)
            i += 1
            continue

        if in_fence and _line_signals_markdown_outside_fence(line):
            out.append("```")
            out.append("")
            in_fence = False
            inserted_mid_close = True
            continue

        out.append(line)
        i += 1

    result = "\n".join(out)
    if inserted_mid_close:
        result = result.rstrip("\n")
        tail_lines = result.split("\n")
        while tail_lines and tail_lines[-1].strip() == "":
            tail_lines.pop()
        if tail_lines and tail_lines[-1].strip() == "```":
            tail_lines.pop()
            result = "\n".join(tail_lines)
            if result and not result.endswith("\n"):
                result += "\n"
    return result


def normalize_markdown_fences(content: str) -> str:
    """Repair prose leaked inside fences, then balance odd ``` counts."""
    content = repair_leaked_markdown_fences(content)
    content = balance_markdown_fences(content)
    return content


def balance_markdown_fences(content: str) -> str:
    """If markdown has an odd number of ``` fence lines, append a closing fence.

    Models sometimes omit the closing fence, which makes the rest of the article
    parse as one code block (images and headings never render as HTML).
    """
    if not content:
        return content
    lines = content.splitlines()
    fence_lines = sum(1 for line in lines if _FENCE_LINE.match(line))
    if fence_lines % 2 == 1:
        if not content.endswith("\n"):
            content += "\n"
        content += "```\n"
    return content


def fix_tables(content: str) -> str:
    """Fix markdown table separators for likely table blocks only."""
    lines = content.split("\n")
    fixed_lines = []

    def _pipe_count(text: str) -> int:
        return text.count("|")

    def _is_probable_table_header(text: str) -> bool:
        s = text.strip()
        if not s or s.startswith("```"):
            return False
        # Avoid rewriting obvious prose/sentences that include pipes.
        if s.startswith("- ") or s.startswith("* ") or s.startswith(">"):
            return False
        return _pipe_count(text) >= 2

    def _is_table_separator(text: str) -> bool:
        return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", text))

    def _normalize_table_row(text: str, expected_cols: int) -> str:
        s = text.strip()
        if not s.startswith("|"):
            s = "| " + s
        if not s.endswith("|"):
            s = s + " |"
        col_count = _pipe_count(s) - 1
        if col_count < expected_cols:
            s = s[:-1] + (" |" * (expected_cols - col_count)) + "|"
        return s

    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if _FENCE_LINE.match(line):
            in_fence = not in_fence
            fixed_lines.append(line)
            i += 1
            continue

        # Only treat as a table when we can confirm a minimum shape:
        # header row + at least one more pipe row.
        if (not in_fence) and _is_probable_table_header(line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            if _pipe_count(next_line) >= 2:
                header_line = _normalize_table_row(line, _pipe_count(line) - 1)

                if _is_table_separator(next_line):
                    sep_line = _normalize_table_row(next_line, _pipe_count(header_line) - 1)
                    row_start = i + 2
                else:
                    cols = max(_pipe_count(header_line) - 1, 1)
                    sep_line = "| " + " | ".join(["---"] * cols) + " |"
                    row_start = i + 1

                # Require at least one body row to avoid false positives on prose.
                if row_start < len(lines) and _pipe_count(lines[row_start]) >= 2:
                    fixed_lines.append(header_line)
                    fixed_lines.append(sep_line)
                    i = row_start
                    while i < len(lines) and _pipe_count(lines[i]) >= 2:
                        fixed_lines.append(
                            _normalize_table_row(lines[i], _pipe_count(header_line) - 1)
                        )
                        i += 1
                    continue

            fixed_lines.append(line)
            i += 1
        else:
            fixed_lines.append(line)
            i += 1

    return "\n".join(fixed_lines)


_MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _image_tail_already_attributed(tail: str) -> bool:
    """True if the text right after an image markdown already credits the source."""
    t = tail.lstrip()
    if not t:
        return False
    if t[0] in "*_":
        head = t[:160].lower()
        if "photo" in head or "source" in head or "credit" in head or "original" in head:
            return True
    return False


def _image_url_is_fetchable(url: str) -> bool:
    """Best-effort check that a URL responds as an image."""
    if not url:
        return False
    if url in _IMAGE_URL_CHECK_CACHE:
        return _IMAGE_URL_CHECK_CACHE[url]

    ok = False
    try:
        response = requests.head(url, allow_redirects=True, timeout=_IMAGE_URL_CHECK_TIMEOUT_SECONDS)
        content_type = (response.headers.get("content-type") or "").lower()
        if response.status_code < 400 and content_type.startswith("image/"):
            ok = True
        elif response.status_code < 400:
            # Some origins don't expose useful HEAD content-type; try GET fallback.
            response = requests.get(url, stream=True, allow_redirects=True, timeout=_IMAGE_URL_CHECK_TIMEOUT_SECONDS)
            content_type = (response.headers.get("content-type") or "").lower()
            ok = response.status_code < 400 and content_type.startswith("image/")
    except Exception:
        ok = False

    _IMAGE_URL_CHECK_CACHE[url] = ok
    return ok


def _image_domain_is_allowed(url: str) -> bool:
    """Allow inline image embeds only from configured domains when set."""
    if not _INLINE_IMAGE_ALLOWED_DOMAINS:
        return True
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        return False
    host = host.split(":")[0]
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in _INLINE_IMAGE_ALLOWED_DOMAINS)


def process_inline_images(content: str, source_name: str, source_url: str) -> str:
    """Strip hotlinked images or append attribution pointing at the cited article."""
    if not content:
        return content

    if _STRIP_MARKDOWN_IMAGES:

        def strip_repl(match: re.Match) -> str:
            alt = (match.group(1) or "").strip() or "Photo"
            label = source_name or "original article"
            if source_url.strip():
                return (
                    f"*{alt}: not embedded on this site; "
                    f"[open the original article ({label})]({source_url}) to view it.*"
                )
            return f"*{alt} (image omitted).*"

        return _MARKDOWN_IMAGE.sub(strip_repl, content)

    if not source_url.strip():
        return content

    parts: List[str] = []
    last = 0
    label = source_name.strip() or "Original article"
    for m in _MARKDOWN_IMAGE.finditer(content):
        alt = (m.group(1) or "").strip() or "Photo"
        image_url = (m.group(2) or "").strip()
        if not _image_domain_is_allowed(image_url):
            label = source_name.strip() or "original article"
            parts.append(content[last : m.start()])
            if source_url.strip():
                parts.append(
                    f"*{alt}: image omitted due to site embedding policy; "
                    f"[open the original article ({label})]({source_url}) to view it.*"
                )
            else:
                parts.append(f"*{alt} (image omitted due to site embedding policy).*")
            last = m.end()
            continue

        if _VERIFY_INLINE_IMAGES and not _image_url_is_fetchable(image_url):
            label = source_name.strip() or "original article"
            if source_url.strip():
                parts.append(content[last : m.start()])
                parts.append(
                    f"*{alt}: image not available from source CDN right now; "
                    f"[open the original article ({label})]({source_url}) to view context.*"
                )
            else:
                parts.append(content[last : m.start()])
                parts.append(f"*{alt} (image omitted; original image URL unavailable).*")
            last = m.end()
            continue

        parts.append(content[last : m.end()])
        tail = content[m.end() : m.end() + 800]
        if source_url in tail or _image_tail_already_attributed(tail):
            last = m.end()
            continue
        parts.append(
            f"\n\n*Image: shown as in source reporting. "
            f"Credit and license belong to the rights holder; see "
            f"[{label}]({source_url}) for the original context.*\n\n"
        )
        last = m.end()
    parts.append(content[last:])
    return "".join(parts)


def sanitize_ai_content(
    title: str,
    content: str,
    source_name: str = "",
    source_url: str = "",
) -> str:
    """Sanitize AI-generated content to fix common issues."""
    content = html.unescape(content)
    
    content = re.sub(r'^#+\s*' + re.escape(title) + r'\s*$', '', content, flags=re.MULTILINE)
    
    content = re.sub(r'^' + re.escape(title) + r'\s*$', '', content, flags=re.MULTILINE)
    
    title_words = title.lower().split()
    if len(title_words) >= 3:
        first_3 = ' '.join(title_words[:3])
        content = re.sub(r'^#+\s*' + re.escape(first_3) + r'\s*$', '', content, flags=re.MULTILINE)
    
    content = fix_code_blocks(content)

    content = normalize_markdown_fences(content)

    content = fix_tables(content)
    
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    content = re.sub(r' +$', '', content, flags=re.MULTILINE)
    
    content = content.strip()

    content = process_inline_images(content, source_name, source_url)

    return content


def build_user_prompt(
    topic: str,
    article_content: str,
    source_name: str,
    source_url: str,
    source_char_limit: int,
) -> str:
    """Build a consistent user prompt across model providers."""
    return f"""Write a blog post about this technology news story:

Topic: {topic}

Source Material:
{article_content[:source_char_limit]}

Source: {source_name}
Link: {source_url}

Editorial rules:
- Lead with the technology relevance, not generic news framing.
- Use this content structure when possible: opening paragraph, ## What Happened, ## Why It Matters, ## What To Watch.
- If this is only weakly technology-related, keep the article concise and state the limited tech relevance.
- Write one complete-sentence excerpt under 180 characters.
- Return 3-5 specific tags from the topic area; never return only "Tech News".

Image policy: Only embed `![alt](url)` if that exact URL appears in Source Material. Otherwise describe the image and point readers to the link above. When you embed, add a one-line credit under the image pointing to the article URL.

Close every ``` code fence before body text after the code.
Return JSON with exactly these keys only: title, slug, tldr, content, excerpt, tags.
Do not include source_url, cover_image, ai_model, or any extra keys.
If the source does not support a claim, state uncertainty instead of guessing.
Generate a compelling, well-structured post in JSON format."""


def _coerce_list_of_strings(value: Any) -> List[str]:
    """Normalize values to a non-empty list of strings."""
    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


_TAG_DISPLAY_NAMES = {
    "security": "Security",
    "cloud": "Cloud",
    "devops": "DevOps",
    "llm": "AI",
    "gpu": "Hardware",
    "ml": "AI",
    "robotics": "Robotics",
    "agent": "AI Agents",
    "research": "Research",
    "startup": "Startups",
    "hardware": "Hardware",
    "quantum": "Quantum",
}

_GENERIC_TAGS = {"tech news", "technology", "news", "breaking"}


def _fallback_tags(title: str, content: str, source_name: str = "") -> List[str]:
    """Derive specific fallback tags from known keyword/category mappings."""
    haystack = f"{title} {content[:1500]} {source_name}".lower()
    tags: List[str] = []
    for keyword, category in KEYWORD_MAP.items():
        if keyword in haystack:
            label = _TAG_DISPLAY_NAMES.get(category, category.title())
            if label not in tags:
                tags.append(label)
        if len(tags) >= 5:
            break

    if not tags:
        tags = ["Developer Tools"] if any(
            token in haystack for token in ("developer", "github", "open source", "programming")
        ) else ["Technology"]
    return tags[:5]


def _normalize_tags(tags: List[str], title: str, content: str, source_name: str) -> List[str]:
    """Keep tags specific enough for topic filtering and avoid single generic tags."""
    cleaned: List[str] = []
    for tag in tags:
        safe = re.sub(r"\s+", " ", html.unescape(str(tag))).strip()
        if not safe:
            continue
        if safe.lower() in _GENERIC_TAGS:
            continue
        if safe not in cleaned:
            cleaned.append(safe[:30])

    fallback = _fallback_tags(title, content, source_name)
    for tag in fallback:
        if tag not in cleaned:
            cleaned.append(tag)

    return cleaned[:5]


def _plain_text_from_markdown(content: str) -> str:
    """Produce readable text for excerpt fallback without markdown syntax."""
    text = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>|-]+", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _complete_sentence_excerpt(text: str, max_chars: int = 180) -> str:
    """Return a complete sentence without cutting off mid-thought."""
    cleaned = _plain_text_from_markdown(text)
    if not cleaned:
        return ""
    sentence_match = re.search(r"(.{40,}?[.!?])(?:\s|$)", cleaned)
    if sentence_match and len(sentence_match.group(1)) <= max_chars:
        return sentence_match.group(1).strip()

    snippet = cleaned[:max_chars].rstrip()
    boundary = max(snippet.rfind(", "), snippet.rfind("; "), snippet.rfind(": "), snippet.rfind(" "))
    if boundary >= 80:
        snippet = snippet[:boundary].rstrip()
    return snippet.rstrip(".!?;:,") + "."


def _record_normalization_fallbacks(
    model_name: str, fallback_fields: List[str], extra_keys: List[str]
) -> None:
    """Track how often we rely on fallback normalization fields."""
    if not fallback_fields and not extra_keys:
        return

    with _NORMALIZATION_METRICS_LOCK:
        for field in fallback_fields:
            _NORMALIZATION_FALLBACK_COUNTS[field] = (
                _NORMALIZATION_FALLBACK_COUNTS.get(field, 0) + 1
            )
            if model_name:
                if model_name not in _NORMALIZATION_FALLBACK_BY_MODEL:
                    _NORMALIZATION_FALLBACK_BY_MODEL[model_name] = {}
                model_bucket = _NORMALIZATION_FALLBACK_BY_MODEL[model_name]
                model_bucket[field] = model_bucket.get(field, 0) + 1
        if extra_keys:
            _NORMALIZATION_FALLBACK_COUNTS["extra_keys_dropped"] = (
                _NORMALIZATION_FALLBACK_COUNTS.get("extra_keys_dropped", 0)
                + len(extra_keys)
            )
            if model_name:
                if model_name not in _NORMALIZATION_FALLBACK_BY_MODEL:
                    _NORMALIZATION_FALLBACK_BY_MODEL[model_name] = {}
                model_bucket = _NORMALIZATION_FALLBACK_BY_MODEL[model_name]
                model_bucket["extra_keys_dropped"] = (
                    model_bucket.get("extra_keys_dropped", 0) + len(extra_keys)
                )

    logger.info(
        "    Normalization fallback used (%s): %s%s",
        model_name,
        ", ".join(fallback_fields) if fallback_fields else "none",
        f" | dropped extra keys: {', '.join(extra_keys)}" if extra_keys else "",
    )


def get_normalization_fallback_counts() -> Dict[str, int]:
    """Return a snapshot of normalization fallback counters for summaries."""
    with _NORMALIZATION_METRICS_LOCK:
        return dict(_NORMALIZATION_FALLBACK_COUNTS)


def get_normalization_fallbacks_by_model() -> Dict[str, Dict[str, int]]:
    """Return model-attributed fallback counters for summaries."""
    with _NORMALIZATION_METRICS_LOCK:
        return {
            model: dict(counts)
            for model, counts in _NORMALIZATION_FALLBACK_BY_MODEL.items()
            if counts
        }


def validate_and_normalize_result(
    result: Dict[str, Any],
    topic: str,
    source_name: str,
    source_url: str,
    fallback_fields: Optional[List[str]] = None,
    extra_keys: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Validate and normalize AI output to the expected schema."""
    if not isinstance(result, dict):
        return None

    fallback_log = fallback_fields if fallback_fields is not None else []
    extra_log = extra_keys if extra_keys is not None else []
    allowed_keys = {"title", "slug", "tldr", "content", "excerpt", "tags"}
    dropped_keys = sorted(str(k) for k in result.keys() if str(k) not in allowed_keys)
    extra_log.extend(dropped_keys)

    title = str(result.get("title", "")).strip() or topic.strip()
    if not str(result.get("title", "")).strip():
        fallback_log.append("title_defaulted")
    content = str(result.get("content", "")).strip()
    excerpt = str(result.get("excerpt", "")).strip()

    if not content:
        return None

    slug = str(result.get("slug", "")).strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        fallback_log.append("slug_regenerated")
        base = re.sub(r"[^a-z0-9-]", "-", title.lower())
        slug = re.sub(r"-+", "-", base).strip("-")[:80] or "post"

    tldr = _coerce_list_of_strings(result.get("tldr", []))
    if not tldr:
        fallback_log.append("tldr_defaulted")
        tldr = [f"Update: {title}", f"Source: {source_name or 'Tech news'}"]
    tldr = tldr[:5]

    raw_tags = _coerce_list_of_strings(result.get("tags", []))
    tags = _normalize_tags(raw_tags, title, content, source_name)
    if not raw_tags or raw_tags == ["Tech News"]:
        fallback_log.append("tags_defaulted")
    tags = tags[:5]
    if not excerpt:
        fallback_log.append("excerpt_defaulted")

    excerpt_text = _complete_sentence_excerpt(excerpt, 180)
    if not excerpt_text:
        excerpt_text = _complete_sentence_excerpt(content, 180)
    if not excerpt_text:
        excerpt_text = f"Technology update from {source_name or 'the source'}."

    normalized: Dict[str, Any] = {
        "title": title,
        "slug": slug,
        "tldr": tldr,
        "content": sanitize_ai_content(title, content, source_name, source_url),
        "excerpt": excerpt_text,
        "tags": tags,
        "source_url": [{"name": source_name, "url": source_url}],
    }
    return normalized


def finalize_result(
    result: Dict[str, Any],
    model_name: str,
    topic: str,
    source_name: str,
    source_url: str,
) -> Optional[Dict[str, Any]]:
    """Validate, sanitize, and append common metadata."""
    fallback_fields: List[str] = []
    extra_keys: List[str] = []
    normalized = validate_and_normalize_result(
        result,
        topic,
        source_name,
        source_url,
        fallback_fields=fallback_fields,
        extra_keys=extra_keys,
    )
    if not normalized:
        logger.warning("    Generated payload failed schema validation")
        return None

    _record_normalization_fallbacks(model_name, fallback_fields, extra_keys)

    normalized["cover_image"] = get_cover_image(
        normalized.get("title", topic), normalized.get("content", "")
    )
    normalized["ai_model"] = model_name
    return normalized


def generate_with_gemini(topic: str, article_content: str, source_name: str, source_url: str) -> Optional[Dict[str, Any]]:
    """Generate blog post using Google Gemini."""
    if not GOOGLE_API_KEY:
        return None
    
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )
        
        user_prompt = build_user_prompt(
            topic, article_content, source_name, source_url, source_char_limit=4000
        )

        response = model.generate_content(user_prompt)
        text = response.text
        
        input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else estimate_tokens(article_content[:4000])
        output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else estimate_tokens(text)
        cost_tracker.track_request(GEMINI_MODEL, input_tokens, output_tokens)
        
        result = recover_json(text)
        if not result:
            logger.warning(f"    Failed to parse JSON response")
            return None

        return finalize_result(result, GEMINI_MODEL, topic, source_name, source_url)
        
    except Exception as e:
        logger.warning(f"    Gemini error: {e}")
        return None


def generate_with_openrouter(topic: str, article_content: str, source_name: str, source_url: str) -> Optional[Dict[str, Any]]:
    """Generate blog post using OpenRouter (Llama)."""
    if not OPENROUTER_API_KEY:
        return None
    
    try:
        client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL
        )
        
        user_prompt = build_user_prompt(
            topic, article_content, source_name, source_url, source_char_limit=8000
        )

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        text = response.choices[0].message.content
        logger.debug(f"    Raw response length: {len(text)}")
        
        input_tokens = response.usage.prompt_tokens if hasattr(response, 'usage') else estimate_tokens(article_content[:8000])
        output_tokens = response.usage.completion_tokens if hasattr(response, 'usage') else estimate_tokens(text)
        cost_tracker.track_request(OPENROUTER_MODEL, input_tokens, output_tokens)
        
        result = recover_json(text)
        if not result:
            logger.warning(f"    Failed to parse JSON response")
            return None

        return finalize_result(result, OPENROUTER_MODEL, topic, source_name, source_url)
        
    except json.JSONDecodeError as e:
        logger.warning(f"    JSON parse error: {e}")
        logger.warning(f"    Response preview: {text[:200]}...")
        return None
    except Exception as e:
        logger.warning(f"    OpenRouter error: {e}")
        return None


def generate_blog_post(topic: str, article_content: str, source_name: str, source_url: str) -> Optional[Dict[str, Any]]:
    """Generate blog post from tech news context; tries Gemini first, then OpenRouter."""
    
    logger.info(f"    Trying Gemini...")
    
    if not cost_tracker.should_continue():
        logger.warning(f"    Budget exhausted, skipping AI generation")
        return None
    
    result = generate_with_gemini(topic, article_content, source_name, source_url)
    if result:
        logger.info(f"    ✓ Gemini succeeded")
        return result
    
    logger.info(f"    Trying OpenRouter...")
    
    if not cost_tracker.should_continue():
        logger.warning(f"    Budget exhausted, skipping fallback")
        return None
    
    result = generate_with_openrouter(topic, article_content, source_name, source_url)
    if result:
        logger.info(f"    ✓ OpenRouter succeeded")
        return result
    
    logger.warning(f"    AI generation failed, no more providers to try")
    return None


def generate_mock_post(topic: str, source_name: str, source_url: str) -> Dict[str, Any]:
    """Generate a fallback mock post when AI fails."""
    timestamp = int(datetime.now().timestamp())
    clean_topic = topic.lower().replace(" ", "-")
    clean_topic = re.sub(r'[^a-z0-9-]', '', clean_topic)
    clean_topic = re.sub(r'-+', '-', clean_topic).strip('-')
    slug = f"{clean_topic[:50]}-{timestamp}"
    
    return {
        "title": topic,
        "slug": slug,
        "tldr": [
            f"Breaking: {topic}",
            f"Source: {source_name}",
            "AI-powered summary unavailable"
        ],
        "content": f"""# {topic}

*Note: This is a placeholder post due to API limitations.*

## Latest Update

{topic} - This is a developing story. Check back for full coverage.

## Why It Matters

This announcement represents a significant development in the AI space. Industry experts are closely monitoring the situation.

## What's Next

Stay tuned for more detailed coverage as more information becomes available.

[Read more on {source_name}]({source_url})
""",
        "excerpt": f"Latest update on {topic} from {source_name}.",
        "tags": ["AI", "Tech News", "Breaking"],
        "source_url": [{"name": source_name, "url": source_url}],
        "cover_image": get_cover_image(topic)
    }


register_summary_provider("normalization_fallbacks", get_normalization_fallback_counts)
register_summary_provider(
    "normalization_fallbacks_by_model", get_normalization_fallbacks_by_model
)


if __name__ == "__main__":
    result = generate_mock_post("OpenAI announces GPT-5", "OpenAI", "https://openai.com")
    print(json.dumps(result, indent=2) if result else "Generation failed")