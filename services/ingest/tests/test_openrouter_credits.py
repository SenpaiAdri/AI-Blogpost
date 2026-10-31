import os
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from infra import openrouter_credits as credits
from pipeline import orchestrator, processor
from pipeline.persistence import BatchSaveResult
from generation import llm_client


class CreditCheckTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {
            "OPEN_ROUTER_API_KEY": "generation-key",
            "OPENROUTER_MANAGEMENT_API_KEY": "management-key",
        }))
        self.stack.enter_context(patch.object(credits, "OPENROUTER_MIN_CREDITS_USD", 0.05))
        self.stack.enter_context(patch.object(credits, "OPENROUTER_MANAGEMENT_API_KEY", "management-key"))
        self.stack.enter_context(patch.object(credits, "wait_for_url"))
        self.get = self.stack.enter_context(patch.object(credits.requests, "get"))
        self.responses(10, 2, None)

    def responses(self, purchased, used, remaining, **extra):
        self.get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"data": {"total_credits": purchased, "total_usage": used}}),
            MagicMock(status_code=200, json=lambda: {"data": {"limit_remaining": remaining, **extra}}),
        ]

    def test_uncapped_key_still_uses_account_balance(self):
        self.assertEqual(credits.check_available_credits(), 8)
        calls = self.get.call_args_list
        self.assertEqual(calls[0].kwargs["headers"]["Authorization"], "Bearer management-key")
        self.assertEqual(calls[1].kwargs["headers"]["Authorization"], "Bearer generation-key")

    def test_transport_prevents_redirects_and_has_timeout(self):
        credits.check_available_credits()
        for call in self.get.call_args_list:
            self.assertFalse(call.kwargs["allow_redirects"])
            self.assertEqual(call.kwargs["timeout"], 10)

    def test_invalid_minimum_cannot_disable_gate(self):
        for minimum in [0, -1, float("nan"), float("inf")]:
            with self.subTest(minimum=minimum), patch.object(credits, "OPENROUTER_MIN_CREDITS_USD", minimum):
                with self.assertRaises(credits.CreditCheckError):
                    credits.check_available_credits()

    def test_missing_or_malformed_response_fields_fail_closed(self):
        for account, key in [
            ({}, {"limit_remaining": None}),
            ({"total_credits": 1, "total_usage": 0}, {}),
            ({"total_credits": 1, "total_usage": 0}, {"limit_remaining": "unknown"}),
            ({"total_credits": 1, "total_usage": 0}, {"limit_remaining": None, "effective_budget": {}}),
        ]:
            self.get.side_effect = [
                MagicMock(status_code=200, json=lambda: {"data": account}),
                MagicMock(status_code=200, json=lambda: {"data": key}),
            ]
            with self.assertRaises(credits.CreditCheckError):
                credits.check_available_credits()

    def test_account_or_key_can_stop_generation(self):
        for purchased, used, remaining in [(10, 9.99, None), (10, 0, 0.01), (10, 11, None), (10, 0, 0)]:
            with self.subTest(remaining=remaining, used=used):
                self.responses(purchased, used, remaining)
                with self.assertRaises(credits.CreditCheckError) as result:
                    credits.check_available_credits()
                self.assertEqual(result.exception.reason, "insufficient_credits")

    def test_effective_budget_is_also_enforced(self):
        self.responses(10, 0, None, effective_budget={"remaining_usd": 0.01})
        with self.assertRaises(credits.CreditCheckError):
            credits.check_available_credits()

    def test_minimum_is_inclusive(self):
        self.responses(10, 0, 0.05)
        self.assertEqual(credits.check_available_credits(), 0.05)
        self.responses(0.15, 0.10, None)
        self.assertEqual(credits.check_available_credits(), 0.05)

    def test_missing_management_key_blocks_without_request(self):
        with patch.object(credits, "OPENROUTER_MANAGEMENT_API_KEY", ""):
            with self.assertRaises(credits.CreditCheckError) as result:
                credits.check_available_credits()
        self.assertEqual(result.exception.reason, "credit_check_failed")
        self.get.assert_not_called()

    def test_api_errors_and_malformed_money_fail_closed(self):
        for bad in [None, True, "8", float("nan"), float("inf")]:
            with self.subTest(bad=bad):
                self.responses(bad, 0, None)
                with self.assertRaises(credits.CreditCheckError):
                    credits.check_available_credits()
        for status in [302, 401, 403, 429, 500]:
            self.get.side_effect = None
            self.get.return_value = MagicMock(status_code=status)
            with self.assertRaises(credits.CreditCheckError):
                credits.check_available_credits()
        self.get.side_effect = requests.Timeout("secret provider text")
        with self.assertRaises(credits.CreditCheckError) as result:
            credits.check_available_credits()
        self.assertNotIn("secret provider text", str(result.exception))


class PipelineCreditTests(unittest.TestCase):
    def run_pipeline(self, checks, outcomes=None):
        with ExitStack() as stack:
            for name, value in {
                "validate_environment": True, "get_supabase_client": MagicMock(),
                "get_active_topic_guidance": [], "get_active_rss_sources": [],
                "get_latest_news": [MagicMock(title=title, source="Feed") for title in ("One", "Two", "Three")],
                "get_all_existing_urls": set(),
            }.items():
                stack.enter_context(patch.object(orchestrator, name, return_value=value))
            stack.enter_context(patch.object(orchestrator.cost_tracker, "should_continue", return_value=True))
            stack.enter_context(patch.object(orchestrator.time, "sleep"))
            stack.enter_context(patch.object(orchestrator, "check_available_credits", side_effect=checks))
            process = stack.enter_context(patch.object(orchestrator, "process_news_item_for_batch", return_value={"title": "saved"}, side_effect=outcomes))
            save = stack.enter_context(patch.object(orchestrator, "batch_save_posts", return_value=BatchSaveResult(True, ["post-1"])))
            summary = stack.enter_context(patch.object(orchestrator, "log_summary"))
            llm_client._failure_reason.set("ai_generation_failed")
            orchestrator.main()
            return process, save, summary.call_args.args[0]

    def test_low_credits_stop_before_processing_and_preserve_pending_posts(self):
        process, save, summary = self.run_pipeline([1, credits.CreditCheckError("insufficient_credits")])
        self.assertEqual(process.call_count, 1)
        self.assertEqual(save.call_args.args[1], [{"title": "saved"}])
        self.assertEqual(summary["new_posts_saved"], 1)
        self.assertEqual(summary["note"], "insufficient_credits")
        self.assertTrue(summary["budget_stopped_early"])

    def test_unavailable_check_preserves_completed_posts(self):
        process, save, summary = self.run_pipeline([1, credits.CreditCheckError("credit_check_failed")])
        self.assertEqual(process.call_count, 1)
        self.assertEqual(summary["new_posts_saved"], 1)
        self.assertEqual(summary["note"], "credit_check_failed")
        self.assertEqual(summary["credit_check_errors"], 1)

    def test_402_stops_subsequent_items_and_saves_pending_posts(self):
        count = 0
        def process_item(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 1:
                return {"title": "saved"}
            llm_client._failure_reason.set("insufficient_credits")
            kwargs["run_stats"]["failed_ai"] = 1
            return None
        process, save, summary = self.run_pipeline([1, 1, 1], outcomes=process_item)
        self.assertEqual(process.call_count, 2)
        self.assertEqual(save.call_args.args[1], [{"title": "saved"}])
        self.assertEqual(summary["note"], "insufficient_credits")
        self.assertTrue(summary["budget_stopped_early"])

    def test_unavailable_check_prevents_processing_and_fails_empty_run(self):
        with self.assertRaises(SystemExit) as result:
            self.run_pipeline([credits.CreditCheckError("credit_check_failed")])
        self.assertEqual(result.exception.code, 1)

    def test_402_does_not_try_fallback(self):
        def fail(*args, **kwargs):
            llm_client._failure_reason.set("insufficient_credits")
            return None
        with patch.object(llm_client, "generate_with_openrouter", side_effect=fail) as generate, patch.object(llm_client.cost_tracker, "should_continue", return_value=True):
            self.assertIsNone(llm_client.generate_blog_post("Title", "Content", "Feed", "https://example.com"))
        self.assertEqual(generate.call_count, 1)


    def test_402_does_not_retry_item(self):
        def fail(*args, **kwargs):
            llm_client._failure_reason.set("insufficient_credits")
            return None
        item = MagicMock(title="Article", link="https://example.com/article")
        stats = {}
        with patch.object(processor, "generate_blog_post", side_effect=fail) as generate, patch.object(processor, "scrape_article", return_value="Article"), patch.object(processor, "matched_topic_ids", return_value=[]), patch.object(processor, "format_context_for_ai", return_value="Context"), patch.object(processor, "log_ai_generation_result"), patch.object(processor.time, "sleep") as sleep:
            self.assertIsNone(processor._generate_validated_post(MagicMock(), item, "Feed", [], 2, stats))
        self.assertEqual(generate.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(stats["failed_ai"], 1)
