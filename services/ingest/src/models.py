from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Any
import re
import html

from security import (
    validate_url, sanitize_text, generate_safe_slug, 
    MAX_TITLE_LENGTH, MAX_CONTENT_LENGTH, MIN_BLOG_CONTENT_CHARS, MAX_EXCERPT_LENGTH
)

from datetime import datetime

class SourceModel(BaseModel):
    name: str
    url: str

    @field_validator('url')
    @classmethod
    def check_url(cls, v: str) -> str:
        if not validate_url(v):
            raise ValueError(f"Invalid or disallowed URL: {v}")
        return v

class PostInsertModel(BaseModel):
    title: str = Field(..., max_length=MAX_TITLE_LENGTH)
    slug: str = Field(default="")
    content: str = Field(..., max_length=MAX_CONTENT_LENGTH)
    excerpt: str = Field(default="")
    tldr: List[str] = Field(..., min_length=1, max_length=5)
    source_url: List[SourceModel] = Field(..., min_length=1)
    tags: List[str] = Field(..., min_length=1, max_length=5)
    ai_model: Optional[str] = "gemini-2.5-flash"
    is_published: bool = True
    published_at: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
    cover_image: Optional[str] = "https://images.unsplash.com/photo-1677442136019-21780ecad995"

    @field_validator('title', mode='before')
    @classmethod
    def clean_title(cls, v: Any) -> str:
        if not isinstance(v, str):
            v = str(v)
        return re.sub(r"\s+", " ", html.unescape(v).strip())

    @field_validator('content', mode='before')
    @classmethod
    def check_content_length(cls, v: Any) -> str:
        if not isinstance(v, str):
            v = str(v)
        if len(v) > MAX_CONTENT_LENGTH:
            v = v[:MAX_CONTENT_LENGTH]
        if len(v.strip()) < MIN_BLOG_CONTENT_CHARS:
            raise ValueError(f"Content must be at least {MIN_BLOG_CONTENT_CHARS} characters")
        return v

    @field_validator('tldr', mode='before')
    @classmethod
    def clean_tldr(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("tldr must be a list")
        cleaned = [sanitize_text(str(item), 200) for item in v if str(item).strip()]
        if not cleaned:
            raise ValueError("tldr must have at least 1 non-empty item")
        return cleaned[:5]

    @field_validator('tags', mode='before')
    @classmethod
    def clean_tags(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("tags must be a list")
        cleaned = [sanitize_text(str(item), 50)[:30] for item in v if str(item).strip()]
        if not cleaned:
            raise ValueError("tags must have at least 1 non-empty item")
        return cleaned[:5]

    @model_validator(mode='after')
    def generate_slug_and_excerpt(self) -> 'PostInsertModel':
        if not self.slug:
            self.slug = generate_safe_slug(self.title)
        else:
            self.slug = generate_safe_slug(self.slug)
            
        if self.excerpt:
            self.excerpt = sanitize_text(str(self.excerpt), MAX_EXCERPT_LENGTH)
        else:
            # Generate excerpt from content if missing
            self.excerpt = sanitize_text(self.content, MAX_EXCERPT_LENGTH)
            if len(self.content) > MAX_EXCERPT_LENGTH:
                self.excerpt = self.excerpt[:MAX_EXCERPT_LENGTH - 3] + "..."
            
        return self
