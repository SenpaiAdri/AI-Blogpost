import unittest
import sys
from pathlib import Path

backend_src = Path(__file__).resolve().parents[1] / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from main import resolve_display_source_name


class SourceAttributionTests(unittest.TestCase):
    def test_hacker_news_best_uses_original_publisher(self):
        source = resolve_display_source_name(
            "Hacker News Best", "https://github.com/anthropics/claude-code/issues/45756"
        )
        self.assertEqual(source, "GitHub")

    def test_hacker_news_uses_domain_when_mapped(self):
        source = resolve_display_source_name(
            "Hacker News", "https://bsky.app/profile/serenityforge.com/post/3mj3r4nbiws2t"
        )
        self.assertEqual(source, "Bluesky")

    def test_non_aggregator_source_is_preserved(self):
        source = resolve_display_source_name(
            "The Verge", "https://www.theverge.com/2026/04/14/example"
        )
        self.assertEqual(source, "The Verge")


if __name__ == "__main__":
    unittest.main()
