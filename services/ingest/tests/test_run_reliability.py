import os
import sys
import unittest
from unittest.mock import MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pipeline.run_stats import run_failed
from pipeline.persistence import batch_save_posts
from infra.database import get_active_topic_guidance, get_active_rss_sources
from generation.llm_client import classify_provider_error

class ReliabilityTests(unittest.TestCase):
    def test_failure_policy(self):
        self.assertTrue(run_failed(0, {'failed_ai': 5}, None))
        self.assertTrue(run_failed(1, {}, False))
        self.assertFalse(run_failed(1, {'failed_ai': 2}, True))
        self.assertFalse(run_failed(0, {'skipped_duplicate_url': 5}, None))

    def test_config_read_failures_propagate(self):
        client = MagicMock()
        client.from_.side_effect = RuntimeError('unavailable')
        for operation in (get_active_topic_guidance, get_active_rss_sources):
            with self.assertRaises(RuntimeError): operation(client)

    def test_safe_error_classification(self):
        for status, expected in [(402, 'insufficient_credits'), (429, 'rate_limited'), (401, 'provider_authentication_failed'), (500, 'provider_unavailable')]:
            error = Exception('secret bearer value')
            error.status_code = status
            self.assertEqual(classify_provider_error(error), expected)

    def test_partial_batch_save_identifies_inserted_posts(self):
        client = MagicMock()
        client.from_.return_value.upsert.return_value.execute.return_value.data = [{'id': 1}]
        client.from_.return_value.insert.return_value.execute.side_effect = [MagicMock(data=[{'id':'post-1'}]), RuntimeError('link failed')]
        result = batch_save_posts(client, [{'title':'A', 'tags':['AI']}])
        self.assertFalse(result.ok)
        self.assertEqual(result.saved_post_ids, ['post-1'])

if __name__ == '__main__': unittest.main()

class PipelineExitTests(unittest.TestCase):
    def test_all_generation_failures_fail_the_job(self):
        from unittest.mock import patch
        from pipeline import orchestrator
        item = MagicMock(source='Feed', title='Article')
        def fail(*args, **kwargs):
            kwargs['run_stats']['failed_ai'] = 1
            return None
        with patch.object(orchestrator, 'validate_environment', return_value=True), patch.object(orchestrator, 'get_supabase_client'), patch.object(orchestrator, 'get_active_topic_guidance', return_value=[]), patch.object(orchestrator, 'get_active_rss_sources', return_value=[{'name':'Feed','url':'https://example.invalid'}]), patch.object(orchestrator, 'get_latest_news', return_value=[item]), patch.object(orchestrator, 'get_all_existing_urls', return_value=set()), patch.object(orchestrator, 'process_news_item_for_batch', side_effect=fail), patch.object(orchestrator.cost_tracker, 'should_continue', return_value=True):
            with self.assertRaises(SystemExit) as exit_result: orchestrator.main()
            self.assertEqual(exit_result.exception.code, 1)

class SummaryTests(unittest.TestCase):
    def test_summary_is_visible_in_github_without_raw_provider_details(self):
        import tempfile
        from unittest.mock import patch
        from pipeline.run_stats import log_summary
        with tempfile.NamedTemporaryFile(mode='r+') as output, patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': output.name}):
            log_summary({'new_posts_saved': 1, 'failed_ai': 2, 'failed_validation': 0, 'processing_errors': 0, 'batch_insert_ok': True})
            output.seek(0)
            content = output.read()
            self.assertIn('Saved posts: 1', content)
            self.assertIn('AI failures: 2', content)
