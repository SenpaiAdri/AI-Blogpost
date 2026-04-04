import os
import json
import re
import google.generativeai as genai
from typing import Optional, Dict, Any
from datetime import datetime

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

MODEL_NAME = "gemini-2.0-flash-lite"


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
- Content should be in Markdown format with proper headings
- Tone: Professional, enthusiastic, yet critical/technical
- Include code examples if relevant
- No introductory text, just the JSON
- Make the content informative and useful for developers"""


def generate_blog_post(topic: str, article_content: str, source_name: str, source_url: str) -> Optional[Dict[str, Any]]:
    """Generate a blog post from AI news using Gemini."""
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT
    )
    
    user_prompt = f"""Write a blog post about this AI news:

Topic: {topic}

Source Material:
{article_content[:8000]}

Source: {source_name}
Link: {source_url}

Generate a compelling, well-structured blog post in JSON format."""

    try:
        response = model.generate_content(user_prompt)
        text = response.text
        
        json_str = text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(json_str)
        
        result["source_url"] = [{"name": source_name, "url": source_url}]
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {text[:500]}")
        return None
    except Exception as e:
        print(f"AI generation error: {e}")
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
        "source_url": [{"name": source_name, "url": source_url}]
    }


if __name__ == "__main__":
    result = generate_mock_post("OpenAI announces GPT-5", "OpenAI", "https://openai.com")
    print(json.dumps(result, indent=2) if result else "Generation failed")