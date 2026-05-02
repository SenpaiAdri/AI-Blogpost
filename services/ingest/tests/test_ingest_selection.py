import unittest
import sys
from datetime import datetime
from pathlib import Path

backend_src = Path(__file__).resolve().parents[1] / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from ingest import (
    NewsItem,
    diversify_news_items,
    matched_topic_ids,
    normalize_topic_keyword,
    parse_entry_datetime,
    prioritize_news_items_by_topics,
)


class IngestSelectionTests(unittest.TestCase):
    def _item(self, source: str, minute: int) -> NewsItem:
        return NewsItem(
            title=f"{source}-{minute}",
            link=f"https://example.com/{source}/{minute}",
            snippet="snippet",
            source=source,
            pub_date=datetime(2026, 4, 14, 12, minute, 0),
        )

    def test_parse_entry_datetime_rfc2822(self):
        entry = {"published": "Tue, 14 Apr 2026 10:30:00 GMT"}
        dt = parse_entry_datetime(entry, entry["published"])
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 4)
        self.assertEqual(dt.day, 14)
        self.assertEqual(dt.hour, 10)
        self.assertEqual(dt.minute, 30)

    def test_parse_entry_datetime_iso(self):
        entry = {"published": "2026-04-14T10:30:00Z"}
        dt = parse_entry_datetime(entry, entry["published"])
        self.assertEqual(dt, datetime(2026, 4, 14, 10, 30, 0))

    def test_diversify_news_items_caps_single_source(self):
        items = [
            self._item("Hacker News Best", 50),
            self._item("Hacker News Best", 49),
            self._item("Hacker News Best", 48),
            self._item("The Verge", 47),
            self._item("TechCrunch", 46),
        ]
        selected = diversify_news_items(items, limit=4, max_per_source=2)
        sources = [i.source for i in selected]
        self.assertEqual(len(selected), 4)
        self.assertEqual(sources.count("Hacker News Best"), 2)
        self.assertIn("The Verge", sources)
        self.assertIn("TechCrunch", sources)

    def test_normalize_topic_keyword_collapses_case_and_spacing(self):
        self.assertEqual(normalize_topic_keyword("  DeepSeek   Security  "), "deepseek security")

    def test_prioritize_news_items_by_topics_stably_boosts_matches(self):
        items = [
            NewsItem("Generic cloud update", "https://example.com/1", "infra", "A", datetime(2026, 4, 14, 12, 3, 0)),
            NewsItem("DeepSeek releases model", "https://example.com/2", "ai", "B", datetime(2026, 4, 14, 12, 2, 0)),
            NewsItem("Another DeepSeek story", "https://example.com/3", "ai", "C", datetime(2026, 4, 14, 12, 1, 0)),
        ]
        topics = [{"id": "topic-1", "keyword": "DeepSeek", "normalized_keyword": "deepseek", "weight": 3}]

        prioritized = prioritize_news_items_by_topics(items, topics)

        self.assertEqual([item.link for item in prioritized], [
            "https://example.com/2",
            "https://example.com/3",
            "https://example.com/1",
        ])

    def test_matched_topic_ids_returns_only_matching_topics(self):
        item = NewsItem(
            "OpenAI ships security update",
            "https://example.com/security",
            "The vulnerability affects AI tooling.",
            "Example",
            datetime(2026, 4, 14, 12, 0, 0),
        )
        topics = [
            {"id": "security", "keyword": "security", "normalized_keyword": "security", "weight": 1},
            {"id": "robotics", "keyword": "robotics", "normalized_keyword": "robotics", "weight": 1},
        ]

        self.assertEqual(matched_topic_ids(item, topics), ["security"])


if __name__ == "__main__":
    unittest.main()
