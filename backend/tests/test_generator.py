import importlib
import sys
import types
import unittest
from pathlib import Path


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


class FixTablesTests(unittest.TestCase):
    def test_keeps_plain_prose_with_pipe(self):
        content = "Use a|b syntax in regex alternatives, not markdown tables."
        fixed = generator.fix_tables(content)
        self.assertEqual(fixed, content)

    def test_inserts_separator_when_missing(self):
        content = "\n".join(
            [
                "Name | Language | Use",
                "FastAPI | Python | API service",
                "Next.js | TypeScript | Web UI",
            ]
        )
        fixed = generator.fix_tables(content)
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
        fixed = generator.fix_tables(content)
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
        fixed = generator.fix_tables(content)
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
        fixed = generator.fix_tables(content)
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
        fixed = generator.fix_tables(content)
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
        generator._NORMALIZATION_FALLBACK_COUNTS.clear()
        generator._NORMALIZATION_FALLBACK_BY_MODEL.clear()

    def test_tracks_fallback_and_dropped_extra_keys(self):
        raw = {
            "content": "## What happened\n\nSource is still emerging.",
            "unknown_key": "discard-me",
        }
        result = generator.finalize_result(
            raw,
            model_name="test-model",
            topic="Breaking infra update",
            source_name="Example News",
            source_url="https://example.com/story",
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            generator._NORMALIZATION_FALLBACK_COUNTS.get("title_defaulted"), 1
        )
        self.assertEqual(
            generator._NORMALIZATION_FALLBACK_COUNTS.get("slug_regenerated"), 1
        )
        self.assertEqual(
            generator._NORMALIZATION_FALLBACK_COUNTS.get("tldr_defaulted"), 1
        )
        self.assertEqual(
            generator._NORMALIZATION_FALLBACK_COUNTS.get("tags_defaulted"), 1
        )
        self.assertEqual(
            generator._NORMALIZATION_FALLBACK_COUNTS.get("excerpt_defaulted"), 1
        )
        self.assertEqual(
            generator._NORMALIZATION_FALLBACK_COUNTS.get("extra_keys_dropped"), 1
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
        result = generator.finalize_result(
            raw,
            model_name="test-model",
            topic="Ignored topic",
            source_name="Example News",
            source_url="https://example.com/story",
        )

        self.assertIsNotNone(result)
        self.assertEqual(generator._NORMALIZATION_FALLBACK_COUNTS, {})

    def test_metrics_summary_includes_normalization_section(self):
        generator._NORMALIZATION_FALLBACK_COUNTS["tags_defaulted"] = 2
        generator._NORMALIZATION_FALLBACK_BY_MODEL["test-model"] = {"tags_defaulted": 2}
        summary = generator.cost_tracker.get_summary()
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
        generator.finalize_result(
            raw,
            model_name="provider-a",
            topic="Topic A",
            source_name="Source A",
            source_url="https://example.com/a",
        )
        generator.finalize_result(
            raw,
            model_name="provider-b",
            topic="Topic B",
            source_name="Source B",
            source_url="https://example.com/b",
        )
        by_model = generator.get_normalization_fallbacks_by_model()
        self.assertEqual(by_model.get("provider-a", {}).get("title_defaulted"), 1)
        self.assertEqual(by_model.get("provider-b", {}).get("title_defaulted"), 1)
        self.assertEqual(
            by_model.get("provider-a", {}).get("extra_keys_dropped"), 1
        )
        self.assertEqual(
            by_model.get("provider-b", {}).get("extra_keys_dropped"), 1
        )


class InlineImageValidationTests(unittest.TestCase):
    def test_unreachable_image_is_replaced_with_source_link(self):
        original_checker = generator._image_url_is_fetchable
        generator._image_url_is_fetchable = lambda _url: False
        try:
            content = "Intro\n\n![smart glasses design](https://cdn.example.com/a.jpg)\n\nMore"
            out = generator.process_inline_images(
                content,
                source_name="Engadget",
                source_url="https://www.engadget.com/story",
            )
            self.assertNotIn("![smart glasses design]", out)
            self.assertIn("image not available from source CDN right now", out)
            self.assertIn("https://www.engadget.com/story", out)
        finally:
            generator._image_url_is_fetchable = original_checker

    def test_reachable_image_is_kept(self):
        original_checker = generator._image_url_is_fetchable
        generator._image_url_is_fetchable = lambda _url: True
        try:
            content = "![chip photo](https://cdn.example.com/chip.jpg)"
            out = generator.process_inline_images(
                content,
                source_name="Example Source",
                source_url="https://example.com/post",
            )
            self.assertIn("![chip photo](https://cdn.example.com/chip.jpg)", out)
        finally:
            generator._image_url_is_fetchable = original_checker

    def test_disallowed_domain_is_replaced_with_policy_message(self):
        original_checker = generator._image_url_is_fetchable
        original_allow = set(generator._INLINE_IMAGE_ALLOWED_DOMAINS)
        generator._image_url_is_fetchable = lambda _url: True
        generator._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
        generator._INLINE_IMAGE_ALLOWED_DOMAINS.add("images.example.com")
        try:
            content = "![smart glasses](https://cdn.other.com/image.jpg)"
            out = generator.process_inline_images(
                content,
                source_name="Engadget",
                source_url="https://www.engadget.com/story",
            )
            self.assertNotIn("![smart glasses](https://cdn.other.com/image.jpg)", out)
            self.assertIn("image omitted due to site embedding policy", out)
            self.assertIn("https://www.engadget.com/story", out)
        finally:
            generator._image_url_is_fetchable = original_checker
            generator._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
            generator._INLINE_IMAGE_ALLOWED_DOMAINS.update(original_allow)

    def test_allowed_subdomain_is_kept_when_allowlist_enabled(self):
        original_checker = generator._image_url_is_fetchable
        original_allow = set(generator._INLINE_IMAGE_ALLOWED_DOMAINS)
        generator._image_url_is_fetchable = lambda _url: True
        generator._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
        generator._INLINE_IMAGE_ALLOWED_DOMAINS.add("example.com")
        try:
            content = "![photo](https://images.example.com/photo.jpg)"
            out = generator.process_inline_images(
                content,
                source_name="Example",
                source_url="https://example.com/post",
            )
            self.assertIn("![photo](https://images.example.com/photo.jpg)", out)
        finally:
            generator._image_url_is_fetchable = original_checker
            generator._INLINE_IMAGE_ALLOWED_DOMAINS.clear()
            generator._INLINE_IMAGE_ALLOWED_DOMAINS.update(original_allow)


if __name__ == "__main__":
    unittest.main()
