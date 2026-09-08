import importlib.util
import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


def _load_check_script():
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check_rss_feeds.py"
    )
    spec = importlib.util.spec_from_file_location("check_rss_feeds", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_rss_feeds = _load_check_script()


class FakeResponse:
    """Minimal urlopen response stub (context manager with .status)."""

    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, f"reason-{code}", hdrs=None, fp=None)


class RetryClassificationTests(unittest.TestCase):
    def test_retryable_statuses(self):
        for code in (408, 425, 429, 500, 502, 503, 504):
            self.assertTrue(check_rss_feeds.is_retryable_status(code), code)

    def test_permanent_statuses_are_not_retried(self):
        for code in (200, 400, 401, 403, 404, 405, 410):
            self.assertFalse(check_rss_feeds.is_retryable_status(code), code)

    def test_garbage_status_is_not_retried(self):
        self.assertFalse(check_rss_feeds.is_retryable_status(None))
        self.assertFalse(check_rss_feeds.is_retryable_status("oops"))


class CheckFeedRetryTests(unittest.TestCase):
    def test_transient_429_then_success(self):
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if len(calls) < 3:
                raise _http_error(req.full_url, 429)
            return FakeResponse(200)

        with (
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            patch("time.sleep") as mock_sleep,
        ):
            ok, detail = check_rss_feeds.check_feed("Example", "https://example.com/feed")

        self.assertTrue(ok)
        self.assertIn("200", detail)
        self.assertEqual(len(calls), 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_permanent_404_fails_without_retry(self):
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=_http_error("https://example.com/feed", 404),
            ) as mock_open,
            patch("time.sleep") as mock_sleep,
        ):
            ok, detail = check_rss_feeds.check_feed("Example", "https://example.com/feed")

        self.assertFalse(ok)
        self.assertIn("404", detail)
        self.assertEqual(mock_open.call_count, 1)
        mock_sleep.assert_not_called()

    def test_persistent_503_fails_after_max_attempts(self):
        with (
            patch(
                "urllib.request.urlopen",
                side_effect=_http_error("https://example.com/feed", 503),
            ) as mock_open,
            patch("time.sleep"),
        ):
            ok, detail = check_rss_feeds.check_feed("Example", "https://example.com/feed")

        self.assertFalse(ok)
        self.assertIn("503", detail)
        self.assertEqual(mock_open.call_count, check_rss_feeds.MAX_ATTEMPTS)

    def test_timeout_then_success(self):
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if len(calls) == 1:
                raise TimeoutError("timed out")
            return FakeResponse(200)

        with (
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            patch("time.sleep"),
        ):
            ok, _ = check_rss_feeds.check_feed("Example", "https://example.com/feed")

        self.assertTrue(ok)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
