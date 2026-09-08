import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _ensure_src_on_path():
    backend_src = Path(__file__).resolve().parents[1] / "src"
    if str(backend_src) not in sys.path:
        sys.path.insert(0, str(backend_src))


def _ensure_openai_stub():
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


_ensure_src_on_path()
_ensure_openai_stub()

from generation import llm_client as generator


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
        from infra.metrics import TOKEN_PRICING

        for model in (
            generator.OPENROUTER_PRIMARY_MODEL,
            generator.OPENROUTER_FALLBACK_MODEL,
        ):
            self.assertIn(model, TOKEN_PRICING)
            self.assertGreater(TOKEN_PRICING[model]["input"], 0)
            self.assertGreater(TOKEN_PRICING[model]["output"], 0)


class _FakeMessage:
    def __init__(self, content=None, refusal=None):
        self.content = content
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class _FakeUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=20):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeResponse:
    def __init__(self, content, usage="default", finish_reason="stop", refusal=None):
        self.choices = [_FakeChoice(_FakeMessage(content, refusal), finish_reason)]
        self.usage = _FakeUsage() if usage == "default" else usage


class _FakeClient:
    def __init__(self, response):
        self._response = response

    @property
    def chat(self):
        client = self

        class _Completions:
            def create(self, **kwargs):
                return client._response

        class _Chat:
            completions = _Completions()

        return _Chat()


def _valid_payload():
    return {
        "title": "Robustness check post",
        "slug": "robustness-check-post",
        "tldr": ["A", "B", "C"],
        "content": "## New checkpoint ships\n\nAll key details are sourced. " * 20,
        "excerpt": "A new model checkpoint ships with lower inference cost.",
        "tags": ["LLM"],
    }


class GenerateWithOpenRouterRobustnessTests(unittest.TestCase):
    def _call(self, response):
        with (
            patch.object(generator, "OpenAI", return_value=_FakeClient(response)),
            patch.object(generator, "OPENROUTER_API_KEY", "test-key"),
            patch.object(generator, "cost_tracker"),
        ):
            return generator.generate_with_openrouter(
                topic="Robustness check",
                article_content="Source confirms a model release.",
                source_name="Example News",
                source_url="https://example.com/story",
            )

    def test_none_content_returns_none_with_clear_warning(self):
        response = _FakeResponse(
            content=None,
            finish_reason="content_filter",
            refusal="I cannot help with that.",
        )
        with self.assertLogs(generator.logger, level="WARNING") as logctx:
            result = self._call(response)

        self.assertIsNone(result)
        self.assertTrue(
            any("Empty model response" in message for message in logctx.output),
            logctx.output,
        )
        self.assertTrue(
            any("content_filter" in message for message in logctx.output),
            logctx.output,
        )

    def test_none_usage_falls_back_to_estimates(self):
        response = _FakeResponse(content=json.dumps(_valid_payload()), usage=None)
        result = self._call(response)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Robustness check post")

    def test_unparseable_content_logs_preview(self):
        response = _FakeResponse(content="plain prose, no JSON at all {{{")
        with self.assertLogs(generator.logger, level="WARNING") as logctx:
            result = self._call(response)

        self.assertIsNone(result)
        self.assertTrue(
            any("Failed to parse JSON response" in m for m in logctx.output),
            logctx.output,
        )
        self.assertTrue(
            any("Response preview" in m for m in logctx.output),
            logctx.output,
        )

    def test_valid_json_with_usage_succeeds(self):
        response = _FakeResponse(content=json.dumps(_valid_payload()))
        result = self._call(response)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Robustness check post")


if __name__ == "__main__":
    unittest.main()
