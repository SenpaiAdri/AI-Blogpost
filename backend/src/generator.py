import os
import json
import re
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

GEMINI_MODEL = "gemini-2.0-flash"
FALLBACK_MODEL = "google/gemma-3n-e4"
OPENROUTER_MODEL = "google/gemma-3n-e4"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


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
        
        json_str = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(json_str)
        
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
        
        # Remove markdown code blocks and control characters
        text = text.replace("```json", "").replace("```", "")
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        text = text.strip()
        
        # Find and extract JSON between { and }
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            logger.warning(f"    No JSON found in response")
            return None
            
        json_str = json_match.group(0)
        result = json.loads(json_str)
        
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