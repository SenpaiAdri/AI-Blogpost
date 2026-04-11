import os
import json
import re
import html
import google.generativeai as genai
from openai import OpenAI
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib

from logger import get_logger
from metrics import cost_tracker, estimate_tokens

logger = get_logger("generator")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "google/gemma-3-27b-it"
OPENROUTER_MODEL = "google/gemma-3-27b-it"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """You are an expert tech blogger for a site called "AI Blogpost".
Your task is to write a high-quality, engaging blog post about the latest AI news.

Output Format: JSON only
The output must be a valid JSON object with the following schema:
{
  "title": "Catchy and descriptive title",
  "slug": "kebab-case-slug-for-url",
  "tldr": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
  "content": "Full markdown content...",
  "excerpt": "Short teaser sentence (max 200 chars)",
  "tags": ["Tag1", "Tag2", "Tag3"],
  "source_url": [{"name": "Source Name", "url": "https://source.url"}]
}

Guidelines:
- Content should be in Markdown format with proper headings (## Heading)
- Use proper markdown code fences: ```python for code blocks, NOT "python" on its own line
- Use standard markdown tables with proper header row and separator row (|---|---|)
- Use actual characters, NEVER use HTML entities like &amp; &lt; &gt; &#x27; &#39; - use ' < > &
- Do NOT repeat the title in the content
- Do NOT include leading # in content - use ## for main sections
- No introductory text, just the JSON object
- Make the content informative and useful for developers"""

KEYWORD_MAP = {
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


def fix_tables(content: str) -> str:
    """Fix common issues with markdown tables."""
    lines = content.split('\n')
    fixed_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if '|' in line and not line.strip().startswith('|'):
            table_start = i
            header_line = line
            
            if i + 1 < len(lines) and '|' in lines[i + 1]:
                sep_line = lines[i + 1]
                
                if not re.match(r'^\|[\s\-:|]*\|', sep_line):
                    cols = header_line.count('|')
                    sep_line = '|' + '---|' * cols
            
            fixed_lines.append(header_line)
            fixed_lines.append(sep_line)
            i += 2
            
            while i < len(lines) and '|' in lines[i]:
                fixed_lines.append(lines[i])
                i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    return '\n'.join(fixed_lines)


def sanitize_ai_content(title: str, content: str) -> str:
    """Sanitize AI-generated content to fix common issues."""
    content = html.unescape(content)
    
    content = re.sub(r'^#+\s*' + re.escape(title) + r'\s*$', '', content, flags=re.MULTILINE)
    
    content = re.sub(r'^' + re.escape(title) + r'\s*$', '', content, flags=re.MULTILINE)
    
    title_words = title.lower().split()
    if len(title_words) >= 3:
        first_3 = ' '.join(title_words[:3])
        content = re.sub(r'^#+\s*' + re.escape(first_3) + r'\s*$', '', content, flags=re.MULTILINE)
    
    content = fix_code_blocks(content)
    
    content = fix_tables(content)
    
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    content = re.sub(r' +$', '', content, flags=re.MULTILINE)
    
    content = content.strip()
    
    return content


def generate_with_gemini(topic: str, article_content: str, source_name: str, source_url: str) -> Optional[Dict[str, Any]]:
    """Generate blog post using Google Gemini."""
    if not GOOGLE_API_KEY:
        return None
    
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT
        )
        
        user_prompt = f"""Write a blog post about this AI news:

Topic: {topic}

Source Material:
{article_content[:4000]}

Source: {source_name}
Link: {source_url}

Generate a compelling, well-structured blog post in JSON format."""

        response = model.generate_content(user_prompt)
        text = response.text
        
        input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else estimate_tokens(article_content[:4000])
        output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else estimate_tokens(text)
        cost_tracker.track_request(GEMINI_MODEL, input_tokens, output_tokens)
        
        result = recover_json(text)
        if not result:
            logger.warning(f"    Failed to parse JSON response")
            return None
        
        if "content" in result:
            result["content"] = sanitize_ai_content(
                result.get("title", topic),
                result["content"]
            )
        
        result["source_url"] = [{"name": source_name, "url": source_url}]
        result["cover_image"] = get_cover_image(result.get("title", topic), result.get("content", ""))
        result["ai_model"] = GEMINI_MODEL
        return result
        
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
        
        user_prompt = f"""Write a blog post about this AI news:

Topic: {topic}

Source Material:
{article_content[:8000]}

Source: {source_name}
Link: {source_url}

Generate a compelling, well-structured blog post in JSON format."""

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
        
        if "content" in result:
            result["content"] = sanitize_ai_content(
                result.get("title", topic),
                result["content"]
            )
        
        result["source_url"] = [{"name": source_name, "url": source_url}]
        result["cover_image"] = get_cover_image(result.get("title", topic), result.get("content", ""))
        result["ai_model"] = OPENROUTER_MODEL
        return result
        
    except json.JSONDecodeError as e:
        logger.warning(f"    JSON parse error: {e}")
        logger.warning(f"    Response preview: {text[:200]}...")
        return None
    except Exception as e:
        logger.warning(f"    OpenRouter error: {e}")
        return None


def generate_blog_post(topic: str, article_content: str, source_name: str, source_url: str) -> Optional[Dict[str, Any]]:
    """Generate blog post - tries Gemini first, then OpenRouter, then returns None."""
    
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


if __name__ == "__main__":
    result = generate_mock_post("OpenAI announces GPT-5", "OpenAI", "https://openai.com")
    print(json.dumps(result, indent=2) if result else "Generation failed")