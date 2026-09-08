import importlib
import sys
import types
import unittest
from pathlib import Path


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

from generation import markdown as markdown_module
from generation import images as images_module
from generation import normalization as normalization_module
from generation import prompts as prompts_module
from infra import metrics as metrics_module


class FixTablesTests(unittest.TestCase):
    def test_keeps_plain_prose_with_pipe(self):
        content = "Use a|b syntax in regex alternatives, not markdown tables."
        fixed = markdown_module.fix_tables(content)
        self.assertEqual(fixed, content)

    def test_inserts_separator_when_missing(self):
        content = "\n".join(
            [
                "Name | Language | Use",
                "FastAPI | Python | API service",
                "Next.js | TypeScript | Web UI",
            ]
        )
        fixed = markdown_module.fix_tables(content)
        expected = "\n".join(
            [
                "| Name | Language | Use |",
                "| --- | --- | --- |",
                "| FastAPI | Python | API service |",
                "| Next.js | TypeScript | Web UI |",
            ]
        )
        self.assertEqual(fixed, expected)

    def test_preserves_existing_separator(self):
        content = "\n".join(
            [
                "| Tool | Category |",
                "| --- | --- |",
                "| Terraform | DevOps |",
            ]
        )
        fixed = markdown_module.fix_tables(content)
        self.assertEqual(fixed, content)

    def test_requires_body_row_to_treat_as_table(self):
        content = "\n".join(
            [
                "Name | Value | Notes",
                "| --- | --- | --- |",
                "",
                "Paragraph after pipes.",
            ]
        )
        fixed = markdown_module.fix_tables(content)
        self.assertEqual(fixed, content)

    def test_does_not_rewrite_rows_inside_code_fence(self):
        content = "\n".join(
            [
                "```text",
                "Name | Language | Use",
                "FastAPI | Python | API service",
                "```",
            ]
        )
        fixed = markdown_module.fix_tables(content)
        self.assertEqual(fixed, content)

    def test_still_repairs_table_after_code_fence(self):
        content = "\n".join(
            [
                "```python",
                "print('Name | Value | Notes')",
                "```",
                "",
                "Name | Value | Notes",
                "Latency | 120ms | p95",
                "Throughput | 2k rps | avg",
            ]
        )
        fixed = markdown_module.fix_tables(content)
        expected = "\n".join(
            [
                "```python",
                "print('Name | Value | Notes')",
                "```",
                "",
                "| Name | Value | Notes |",
                "| --- | --- | --- |",
                "| Latency | 120ms | p95 |",
                "| Throughput | 2k rps | avg |",
            ]
        )
        self.assertEqual(fixed, expected)


class NormalizationTelemetryTests(unittest.TestCase):
    def setUp(self):
        normalization_module._NORMALIZATION_FALLBACK_COUNTS.clear()
        normalization_module._NORMALIZATION_FALLBACK_BY_MODEL.clear()
        # Clear metrics summary providers side-effects between tests.
        metrics_module._SUMMARY_PROVIDERS.pop("normalization_fallbacks", None)
        metrics_module._SUMMARY_PROVIDERS.pop("normalization_fallbacks_by_model", None)
        from generation.normalization import (
            get_normalization_fallback_counts,
            get_normalization_fallbacks_by_model,
        )

        metrics_module.register_summary_provider(
            "normalization_fallbacks", get_normalization_fallback_counts
        )
        metrics_module.register_summary_provider(
            "normalization_fallbacks_by_model", get_normalization_fallbacks_by_model
        )

    def test_tracks_fallback_and_dropped_extra_keys(self):
        raw = {
            "content": "## What happened\n\nSource is still emerging.",
            "unknown_key": "discard-me",
        }
        result = normalization_module.finalize_result(
            raw,
            model_name="test-model",
            topic="Breaking infra update",
            source_name="Example News",
            source_url="https://example.com/story",
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            normalization_module._NORMALIZATION_FALLBACK_COUNTS.get("title_defaulted"), 1
        )
        self.assertEqual(
            normalization_module._NORMALIZATION_FALLBACK_COUNTS.get("slug_regenerated"), 1
        )
        self.assertEqual(
            normalization_module._NORMALIZATION_FALLBACK_COUNTS.get("tldr_defaulted"), 1
        )
        self.assertEqual(
            normalization_module._NORMALIZATION_FALLBACK_COUNTS.get("tags_defaulted"), 1
        )
        self.assertEqual(
            normalization_module._NORMALIZATION_FALLBACK_COUNTS.get("excerpt_defaulted"), 1
        )
        self.assertEqual(
            normalization_module._NORMALIZATION_FALLBACK_COUNTS.get("extra_keys_dropped"), 1
        )

    def test_no_fallback_does_not_increment_counters(self):
        raw = {
            "title": "Cloud Control Plane Update",
            "slug": "cloud-control-plane-update",
            "tldr": ["A", "B", "C"],
            "content": "## Update\n\nAll key details are sourced.",
            "excerpt": "Control plane update details.",
            "tags": ["Cloud", "Infra"],
        }
        result = normalization_module.finalize_result(
            raw,
            model_name="test-model",
            topic="Ignored topic",
            source_name="Example News",
            source_url="https://example.com/story",
        )

        self.assertIsNotNone(result)
        self.assertEqual(normalization_module._NORMALIZATION_FALLBACK_COUNTS, {})

    def test_excerpt_is_not_cut_mid_sentence(self):
        raw = {
            "title": "Cloud Control Plane Update",
            "slug": "cloud-control-plane-update",
            "tldr": ["A", "B", "C"],
            "content": "## What Happened\n\nA cloud control plane update shipped today.",
            "excerpt": (
                "A cloud control plane update shipped today with changes for operators "
                "who manage production infrastructure across multiple regions and need"
            ),
            "tags": ["Cloud", "DevOps"],
        }
        result = normalization_module.finalize_result(
            raw,
            model_name="test-model",
            topic="Ignored topic",
            source_name="Example News",
            source_url="https://example.com/story",
        )

        self.assertIsNotNone(result)
        self.assertTrue(result["excerpt"].endswith("."))
        self.assertNotIn(" and need.", result["excerpt"])

    def test_generic_only_tags_are_replaced_with_specific_tags(self):
        raw = {
            "title": "Go WebAssembly RDP Client Lands on GitHub",
            "slug": "go-webassembly-rdp-client",
            "tldr": ["A", "B", "C"],
            "content": "## What Happened\n\nA developer released an open source RDP client built with Go and WebAssembly.",
            "excerpt": "A Go and WebAssembly RDP client shows how browser-based developer tools are evolving.",
            "tags": ["Tech News"],
        }
        result = normalization_module.finalize_result(
            raw,
            model_name="test-model",
            topic="Go WebAssembly RDP Client Lands on GitHub",
            source_name="GitHub",
            source_url="https://example.com/story",
        )

        self.assertIsNotNone(result)
        self.assertNotEqual(result["tags"], ["Tech News"])
        self.assertNotIn("Tech News", result["tags"])
        self.assertGreaterEqual(len(result["tags"]), 1)

    def test_metrics_summary_includes_normalization_section(self):
        normalization_module._NORMALIZATION_FALLBACK_COUNTS["tags_defaulted"] = 2
        normalization_module._NORMALIZATION_FALLBACK_BY_MODEL["test-model"] = {"tags_defaulted": 2}
        summary = metrics_module.cost_tracker.get_summary()
        self.assertIn("extra", summary)
        self.assertIn("normalization_fallbacks", summary["extra"])
        self.assertIn("normalization_fallbacks_by_model", summary["extra"])
        self.assertEqual(
            summary["extra"]["normalization_fallbacks"].get("tags_defaulted"), 2
        )
        self.assertEqual(
            summary["extra"]["normalization_fallbacks_by_model"]
            .get("test-model", {})
            .get("tags_defaulted"),
            2,
        )

    def test_model_attribution_tracks_per_provider(self):
        raw = {
            "content": "## Update\n\nDetails are still limited.",
            "extra_a": "x",
        }
        normalization_module.finalize_result(
            raw,
            model_name="provider-a",
            topic="Topic A",
            source_name="Source A",
            source_url="https://example.com/a",
        )
        normalization_module.finalize_result(
            raw,
            model_name="provider-b",
            topic="Topic B",
            source_name="Source B",
            source_url="https://example.com/b",
        )
        by_model = normalization_module.get_normalization_fallbacks_by_model()
        self.assertEqual(by_model.get("provider-a", {}).get("title_defaulted"), 1)
        self.assertEqual(by_model.get("provider-b", {}).get("title_defaulted"), 1)
        self.assertEqual(
            by_model.get("provider-a", {}).get("extra_keys_dropped"), 1
        )
        self.assertEqual(
            by_model.get("provider-b", {}).get("extra_keys_dropped"), 1
        )


class InlineImageValidationTests(unittest.TestCase):
    def test_strip_is_default_and_links_back_to_source(self):
        original_strip = images_module._STRIP_MARKDOWN_IMAGES
        images_module._STRIP_MARKDOWN_IMAGES = True
        try:
            content = "Intro\n\n![smart glasses design](https://cdn.example.com/a.jpg)\n\nMore"
            out = images_module.process_inline_images(
                content,
                source_name="Engadget",
                source_url="https://www.engadget.com/story",
            )
            self.assertNotIn("![smart glasses design]", out)
            self.assertIn("not embedded on this site", out)
            self.assertIn("https://www.engadget.com/story", out)
        finally:
            images_module._STRIP_MARKDOWN_IMAGES = original_strip

    def test_unreachable_image_is_replaced_with_source_link(self):
        original_checker = images_module._image_url_is_fetchable
        original_strip = images_module._STRIP_MARKDOWN_IMAGES
        images_module._image_url_is_fetchable = lambda _url: False
        images_module._STRIP_MARKDOWN_IMAGES = False
        try:
            content = "Intro\n\n![smart glasses design](https://cdn.example.com/a.jpg)\n\nMore"
            out = images_module.process_inline_images(
                content,
                source_name="Engadget",
                source_url="https://www.engadget.com/story",
            )
            self.assertNotIn("![smart glasses design]", out)
            self.assertIn("image not available from source CDN right now", out)
            self.assertIn("https://www.engadget.com/story", out)
        finally:
            images_module._image_url_is_fetchable = original_checker
            images_module._STRIP_MARKDOWN_IMAGES = original_strip

    def test_reachable_image_is_kept(self):
        original_checker = images_module._image_url_is_fetchable
        original_strip = images_module._STRIP_MARKDOWN_IMAGES
        images_module._image_url_is_fetchable = lambda _url: True
        images_module._STRIP_MARKDOWN_IMAGES = False
        try:
            content = "![chip photo](https://cdn.example.com/chip.jpg)"
            out = images_module.process_inline_images(
                content,
                source_name="Example Source",
                source_url="https://example.com/post",
            )
            self.assertIn("![chip photo](https://cdn.example.com/chip.jpg)", out)
        finally:
            images_module._image_url_is_fetchable = original_checker
            images_module._STRIP_MARKDOWN_IMAGES = original_strip

    def test_disallowed_domain_is_replaced_with_policy_message(self):
        original_checker = images_module._image_url_is_fetchable
        original_allow = set(images_module._INLINE_IMAGE_ALLOWED_DOMAINS)
        original_strip = images_module._STRIP_MARKDOWN_IMAGES
        images_module._image_url_is_fetchable = lambda _url: True
        images_module._STRIP_MARKDOWN_IMAGES = False
        images_module._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
        images_module._INLINE_IMAGE_ALLOWED_DOMAINS.add("images.example.com")
        try:
            content = "![smart glasses](https://cdn.other.com/image.jpg)"
            out = images_module.process_inline_images(
                content,
                source_name="Engadget",
                source_url="https://www.engadget.com/story",
            )
            self.assertNotIn("![smart glasses](https://cdn.other.com/image.jpg)", out)
            self.assertIn("image omitted due to site embedding policy", out)
            self.assertIn("https://www.engadget.com/story", out)
        finally:
            images_module._image_url_is_fetchable = original_checker
            images_module._STRIP_MARKDOWN_IMAGES = original_strip
            images_module._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
            images_module._INLINE_IMAGE_ALLOWED_DOMAINS.update(original_allow)

    def test_allowed_subdomain_is_kept_when_allowlist_enabled(self):
        original_checker = images_module._image_url_is_fetchable
        original_allow = set(images_module._INLINE_IMAGE_ALLOWED_DOMAINS)
        original_strip = images_module._STRIP_MARKDOWN_IMAGES
        images_module._image_url_is_fetchable = lambda _url: True
        images_module._STRIP_MARKDOWN_IMAGES = False
        images_module._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
        images_module._INLINE_IMAGE_ALLOWED_DOMAINS.add("example.com")
        try:
            content = "![photo](https://images.example.com/photo.jpg)"
            out = images_module.process_inline_images(
                content,
                source_name="Example",
                source_url="https://example.com/post",
            )
            self.assertIn("![photo](https://images.example.com/photo.jpg)", out)
        finally:
            images_module._image_url_is_fetchable = original_checker
            images_module._STRIP_MARKDOWN_IMAGES = original_strip
            images_module._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
            images_module._INLINE_IMAGE_ALLOWED_DOMAINS.update(original_allow)


class TopicGuidancePromptTests(unittest.TestCase):
    def test_build_topic_guidance_prompt_section_is_bounded_context(self):
        section = prompts_module.build_topic_guidance_prompt_section([
            {"keyword": "DeepSeek", "normalized_keyword": "deepseek", "weight": 3},
            {"keyword": "AI Security", "normalized_keyword": "ai security", "weight": 2},
        ])

        self.assertIn("Current editorial focus topics: deepseek, ai security.", section)
        self.assertIn("Use these topics only as relevance context", section)
        self.assertIn("Do not invent facts", section)

    def test_build_user_prompt_includes_topic_guidance_when_present(self):
        prompt = prompts_module.build_user_prompt(
            topic="DeepSeek security report",
            article_content="Source confirms a security update.",
            source_name="Example",
            source_url="https://example.com/story",
            source_char_limit=4000,
            active_topics=[{"keyword": "DeepSeek", "normalized_keyword": "deepseek", "weight": 3}],
        )

        self.assertIn("Current editorial focus topics: deepseek.", prompt)
        self.assertIn("Source Material:", prompt)


class ArticleVarietyPromptTests(unittest.TestCase):
    def test_system_prompt_bans_generic_headings(self):
        system = prompts_module.SYSTEM_PROMPT
        self.assertIn("NEVER use these generic headings verbatim", system)
        self.assertIn("What To Watch", system)

    def test_user_prompt_suggests_a_story_shape(self):
        prompt = prompts_module.build_user_prompt(
            topic="New open weights model release",
            article_content="Source confirms a model release.",
            source_name="Example",
            source_url="https://example.com/model-story",
            source_char_limit=4000,
        )
        self.assertIn("Suggested shape for variety:", prompt)
        # The old fixed template must no longer be prescribed ...
        self.assertNotIn("Use this content structure when possible", prompt)
        # ... but the generic headings are named once as banned examples.
        self.assertIn("NEVER the generic", prompt)

    def test_shape_suggestion_rotates_and_is_deterministic(self):
        first = prompts_module.pick_article_shape("Topic A", "https://example.com/a")
        again = prompts_module.pick_article_shape("Topic A", "https://example.com/a")
        self.assertEqual(first, again)
        shapes = {
            prompts_module.pick_article_shape(f"Topic {i}", f"https://example.com/{i}")["name"]
            for i in range(20)
        }
        self.assertGreater(len(shapes), 1)

    def test_finalize_result_writes_no_cover_image(self):
        raw = {
            "title": "Model release",
            "slug": "model-release",
            "tldr": ["A", "B", "C"],
            "content": "## New checkpoint ships\n\nAll key details are sourced.",
            "excerpt": "A new model checkpoint ships with lower inference cost.",
            "tags": ["LLM"],
        }
        result = normalization_module.finalize_result(
            raw,
            model_name="test-model",
            topic="Model release",
            source_name="Example News",
            source_url="https://example.com/story",
        )
        self.assertIsNotNone(result)
        self.assertIsNone(result["cover_image"])


if __name__ == "__main__":
    unittest.main()
