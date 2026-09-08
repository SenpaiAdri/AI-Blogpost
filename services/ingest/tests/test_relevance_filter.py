import unittest
import sys
from datetime import datetime
from pathlib import Path

backend_src = Path(__file__).resolve().parents[1] / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from ingest import NewsItem, filter_tech_news, text_matches_tech_keywords


def _item(title: str, snippet: str = "") -> NewsItem:
    return NewsItem(
        title=title,
        link="https://example.com/x",
        snippet=snippet,
        source="Test",
        pub_date=datetime(2026, 4, 14, 12, 0, 0),
    )


class RelevanceFilterTests(unittest.TestCase):
    def assertKeeps(self, title: str, snippet: str = ""):
        self.assertTrue(
            text_matches_tech_keywords(f"{title} {snippet}"),
            f"expected to KEEP: {title}",
        )
        kept = filter_tech_news([_item(title, snippet)])
        self.assertEqual(len(kept), 1, f"filter dropped: {title}")

    def assertRejects(self, title: str, snippet: str = ""):
        self.assertFalse(
            text_matches_tech_keywords(f"{title} {snippet}"),
            f"expected to REJECT: {title}",
        )
        kept = filter_tech_news([_item(title, snippet)])
        self.assertEqual(len(kept), 0, f"filter kept: {title}")

    # --- Core AI / SWE passes ---

    def test_keeps_ai_model_news(self):
        self.assertKeeps(
            "OpenAI releases GPT-5 with improved reasoning for developers",
            "New large language model with agentic coding benchmarks",
        )

    def test_keeps_swe_tooling_news(self):
        self.assertKeeps(
            "TypeScript 5.6 released with faster type inference",
            "Programming language update for developers on GitHub",
        )

    def test_keeps_open_source_dev_news(self):
        self.assertKeeps(
            "Hugging Face releases open source diffusion transformer",
            "Model weights on github for developers",
        )

    # --- Adjacent requires CORE co-signal ---

    def test_keeps_security_with_ai_angle(self):
        self.assertKeeps(
            "Prompt injection vulnerability hits LangChain AI agents",
            "Exploit affects LLM chatbots built by developers",
        )

    def test_keeps_security_with_dev_angle(self):
        self.assertKeeps(
            "Supply chain attack targets npm package",
            "Malware in javascript library used by developers",
        )

    def test_keeps_bigtech_with_ai_angle(self):
        self.assertKeeps(
            "Apple releases AI coding assistant for Xcode developers",
            "LLM for swift programming",
        )

    def test_rejects_pure_security_patch_news(self):
        self.assertRejects(
            "Microsoft patches zero-day in Windows server with urgent update",
            "Patch Tuesday security breach exploit CVE ransomware",
        )

    def test_rejects_bigtech_general_news(self):
        self.assertRejects(
            "Google removes Doki Doki Literature Club from Google Play",
            "Publisher issued statement on game removal",
        )
        self.assertRejects(
            "Apple has removed most towns in Lebanon from Apple maps?",
            "Hacker News query about mapping data",
        )
        self.assertRejects(
            "iOS 26.6 Public Beta Available, Adds Small Change",
            "Apple iPhone update with minor carrier fix",
        )

    def test_rejects_startup_event_guide(self):
        self.assertRejects(
            "How to apply to Startup Battlefield 2026, what you need ahead of the deadline",
            "TechCrunch startup competition guide for founders",
        )

    def test_rejects_standalone_quantum_robotics(self):
        self.assertRejects(
            "Beyond a Single Quantum Chip: Why the Future of Quantum is Modular",
            "qubit scaling with QPU interconnect",
        )
        self.assertRejects(
            "Humanoid robots 'the future' of car making, says BMW",
            "Factory robotics and automation",
        )

    def test_rejects_earnings_and_funding(self):
        self.assertRejects(
            "Samsung quarterly earnings beat expectations on chip demand",
            "Enterprise revenue and saas growth",
        )
        self.assertRejects(
            "Venture capital funding roundup: 10 enterprise SaaS startups raise",
            "Startup funding enterprise saas",
        )


if __name__ == "__main__":
    unittest.main()
