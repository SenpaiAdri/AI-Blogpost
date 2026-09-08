import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_generator_module():
    backend_src = Path(__file__).resolve().parents[1] / "src"
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))

    # Keep tests independent from external SDK installation status.
    if "google.generativeai" not in sys.modules:
        google_module = types.ModuleType("google")
        google_generativeai = types.ModuleType("google.generativeai")
        google_generativeai.configure = lambda **kwargs: None
        google_generativeai.GenerativeModel = object
        google_module.generativeai = google_generativeai
        sys.modules["google"] = google_module
        sys.modules["google.generativeai"] = google_generativeai

    if "openai" not in sys.modules:
        openai_module = types.ModuleType("openai")
        openai_module.OpenAI = object
        sys.modules["openai"] = openai_module

    return importlib.import_module("generator")


generator = _load_generator_module()


class OpenRouterChainTests(unittest.TestCase):
    def _call(self, *args, **kwargs):
        return generator.generate_blog_post(
            topic="Test topic",
            article_content="Test content",
            source_name="Test Source",
            source_url="https://example.com/story",
            *args,
            **kwargs,
        )

    def test_defaults_point_at_deepseek_primary_and_glm_fallback(self):
        self.assertEqual(
            generator.OPENROUTER_PRIMARY_MODEL, "deepseek/deepseek-v4-flash-0731"
        )
        self.assertEqual(
            generator.OPENROUTER_FALLBACK_MODEL, "z-ai/glm-5.3-flash"
        )

    def test_primary_success_returns_without_fallback(self):
        sentinel = {"title": "Primary wins"}
        with patch.object(
            generator, "generate_with_openrouter", return_value=sentinel
        ) as mock_gen:
            result = self._call()

        self.assertEqual(result, sentinel)
        self.assertEqual(mock_gen.call_count, 1)
        self.assertEqual(
            mock_gen.call_args.kwargs.get("model"),
            generator.OPENROUTER_PRIMARY_MODEL,
        )

    def test_primary_failure_falls_back_to_glm(self):
        sentinel = {"title": "Fallback wins"}
        with patch.object(
            generator,
            "generate_with_openrouter",
            side_effect=[None, sentinel],
        ) as mock_gen:
            result = self._call()

        self.assertEqual(result, sentinel)
        self.assertEqual(mock_gen.call_count, 2)
        models_tried = [
            call.kwargs.get("model") for call in mock_gen.call_args_list
        ]
        self.assertEqual(
            models_tried,
            [
                generator.OPENROUTER_PRIMARY_MODEL,
                generator.OPENROUTER_FALLBACK_MODEL,
            ],
        )

    def test_both_failing_returns_none(self):
        with patch.object(
            generator, "generate_with_openrouter", return_value=None
        ) as mock_gen:
            result = self._call()

        self.assertIsNone(result)
        self.assertEqual(mock_gen.call_count, 2)

    def test_chain_pricing_covers_both_models(self):
        from metrics import TOKEN_PRICING

        for model in (
            generator.OPENROUTER_PRIMARY_MODEL,
            generator.OPENROUTER_FALLBACK_MODEL,
        ):
            self.assertIn(model, TOKEN_PRICING)
            self.assertGreater(TOKEN_PRICING[model]["input"], 0)
            self.assertGreater(TOKEN_PRICING[model]["output"], 0)


if __name__ == "__main__":
    unittest.main()
