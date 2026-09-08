"""Shared selection dataclasses."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsItem:
    title: str
    link: str
    snippet: str
    source: str
    pub_date: datetime


@dataclass(frozen=True)
class ActiveTopic:
    id: str
    keyword: str
    normalized_keyword: str
    weight: int = 1
