import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import os


def _ensure_src_on_path():
    src = Path(__file__).resolve().parents[1] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _ensure_stubs():
    if "supabase" not in sys.modules:
        sys.modules["supabase"] = types.ModuleType("supabase")
    if "dotenv" not in sys.modules:
        dotenv_module = types.ModuleType("dotenv")
        dotenv_module.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv_module
    if "openai" not in sys.modules:
        openai_module = types.ModuleType("openai")
        openai_module.OpenAI = object
        sys.modules["openai"] = openai_module


_ensure_src_on_path()
_ensure_stubs()

from models import CommentInsertModel
from infra import database as database_module
from comments import generator as generator_module
from comments import persistence as persistence_module
from comments import runner as runner_module
import config as config_module


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.calls = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args))
        return self

    def gte(self, *args, **kwargs):
        self.calls.append(("gte", args))
        return self

    def order(self, *args, **kwargs):
        self.calls.append(("order", args, kwargs))
        return self

    def limit(self, *args, **kwargs):
        self.calls.append(("limit", args))
        return self

    def in_(self, *args, **kwargs):
        self.calls.append(("in_", args))
        return self

    def insert(self, *args, **kwargs):
        self.calls.append(("insert", args))
        return self

    def execute(self):
        self.client.queries.append((self.table, self.calls))
        return FakeResponse(self.client.data)


class FakeClient:
    def __init__(self, data):
        self.data = data
        self.queries = []

    def from_(self, table):
        return FakeQuery(self, table)


VALID_BODY = (
    "One thing I'd flag in the post's claim about caching: it holds for read-heavy "
    "feeds, but write-heavy workloads still need invalidation. In my opinion the "
    "tradeoff section should call that out."
)


class CommentConfigEnvTests(unittest.TestCase):
    """Unset GitHub secrets arrive as empty strings; they must mean 'default'."""

    def test_empty_string_falls_back_to_default(self):
        env = {
            "COMMENTS_MODEL": "",
            "COMMENTS_MAX_TOKENS": "",
            "COMMENTS_TEMPERATURE": "",
            "COMMENTS_THRESHOLD": "",
            "COMMENTS_AUTHOR_NAME": "",
        }
        with mock.patch.dict(os.environ, env):
            self.assertEqual(config_module._str_env("COMMENTS_MODEL", "primary"), "primary")
            self.assertEqual(config_module._int_env("COMMENTS_MAX_TOKENS", "600"), 600)
            self.assertAlmostEqual(
                config_module._float_env("COMMENTS_TEMPERATURE", "0.8"), 0.8
            )
            self.assertAlmostEqual(
                config_module._float_env("COMMENTS_THRESHOLD", "7.0"), 7.0
            )
            self.assertEqual(
                config_module._str_env("COMMENTS_AUTHOR_NAME", "Critic AI"), "Critic AI"
            )

    def test_explicit_values_parse(self):
        env = {"COMMENTS_MAX_TOKENS": "100", "COMMENTS_THRESHOLD": "8.5"}
        with mock.patch.dict(os.environ, env):
            self.assertEqual(config_module._int_env("COMMENTS_MAX_TOKENS", "600"), 100)
            self.assertAlmostEqual(
                config_module._float_env("COMMENTS_THRESHOLD", "7.0"), 8.5
            )


class CommentInsertModelTests(unittest.TestCase):
    def test_valid_ai_comment(self):
        model = CommentInsertModel(post_id="123", body=VALID_BODY)
        self.assertEqual(model.author_type, "ai")
        self.assertEqual(model.status, "approved")

    def test_rejects_short_body(self):
        with self.assertRaises(Exception):
            CommentInsertModel(post_id="123", body="Too short!")

    def test_rejects_markdown_image(self):
        with self.assertRaises(Exception):
            CommentInsertModel(post_id="123", body=VALID_BODY + " ![image](http://x/y.png)")

    def test_rejects_pending_with_moderator(self):
        with self.assertRaises(Exception):
            CommentInsertModel(post_id="123", body=VALID_BODY, status="pending", moderated_by="admin")


class CommentDatabaseHelperTests(unittest.TestCase):
    def test_get_recent_posts_queries_published_window(self):
        client = FakeClient([{"id": "1"}])
        rows = database_module.get_recent_posts(client, lookback_hours=72, limit=10)
        self.assertEqual(rows, [{"id": "1"}])
        table, calls = client.queries[0]
        self.assertEqual(table, "posts")
        ops = [c[0] for c in calls]
        self.assertIn("select", ops)
        self.assertIn("gte", ops)
        self.assertIn("order", ops)
        self.assertIn("limit", ops)

    def test_has_approved_ai_comment_true_and_false(self):
        self.assertTrue(database_module.has_approved_ai_comment(FakeClient([{"id": "1"}]), "p1"))
        self.assertFalse(database_module.has_approved_ai_comment(FakeClient([]), "p1"))

    def test_batch_commented_ids(self):
        client = FakeClient([{"post_id": "p1"}, {"post_id": "p2"}])
        ids = database_module.get_approved_ai_commented_post_ids(client, ["p1", "p2", "p3"])
        self.assertEqual(ids, {"p1", "p2"})
        table, calls = client.queries[0]
        self.assertEqual(table, "comments")
        self.assertIn("in_", [c[0] for c in calls])

    def test_batch_commented_ids_empty_input(self):
        client = FakeClient([{"post_id": "p1"}])
        self.assertEqual(database_module.get_approved_ai_commented_post_ids(client, []), set())
        self.assertEqual(client.queries, [])


class FakeUsage:
    def __init__(self, prompt_tokens=10, completion_tokens=20):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)
        self.finish_reason = "stop"


class FakeChatResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]
        self.usage = FakeUsage()


class FakeCompletions:
    """Canned response (or exception) per model name."""

    def __init__(self, by_model):
        self.by_model = by_model
        self.seen_models = []

    def create(self, model=None, **kwargs):
        self.seen_models.append(model)
        behavior = self.by_model.get(model, self.by_model.get("*"))
        if isinstance(behavior, Exception):
            raise behavior
        return FakeChatResponse(behavior)


class FakeChat:
    def __init__(self, by_model):
        self.completions = FakeCompletions(by_model)


class FakeOpenAIClient:
    def __init__(self, by_model):
        self.chat = FakeChat(by_model)

    @property
    def seen_models(self):
        return self.chat.completions.seen_models


SCORE_HIGH = '{"score": 8.5, "reason": "Missing tradeoff on caching"}'
SCORE_LOW = '{"score": 3.0, "reason": "Complete how-to, nothing to add"}'
SAMPLE_POST = {"id": "p1", "slug": "s", "title": "T", "excerpt": "E", "content": "C"}


class CommentGeneratorTests(unittest.TestCase):
    def test_score_parses_json(self):
        client = FakeOpenAIClient({"*": SCORE_HIGH})
        score, reason, model = generator_module.score_post(SAMPLE_POST, client=client)
        self.assertAlmostEqual(score, 8.5)
        self.assertIn("tradeoff", reason)
        self.assertIsNotNone(model)

    def test_score_garbage_tries_fallback_then_zero(self):
        client = FakeOpenAIClient({"*": "not json at all {{{"})
        score, reason, model = generator_module.score_post(SAMPLE_POST, client=client)
        self.assertEqual(score, 0.0)
        self.assertEqual(reason, "score_parse_failed")
        self.assertIsNone(model)
        self.assertEqual(len(client.seen_models), 2)

    def test_score_falls_back_to_second_model(self):
        from config import COMMENTS_FALLBACK_MODEL

        client = FakeOpenAIClient({
            "primary": Exception("boom"),
            COMMENTS_FALLBACK_MODEL: SCORE_HIGH,
        })
        score, _, model = generator_module.score_post(
            SAMPLE_POST, model="primary", client=client
        )
        self.assertEqual(client.seen_models, ["primary", COMMENTS_FALLBACK_MODEL])
        self.assertAlmostEqual(score, 8.5)
        self.assertEqual(model, COMMENTS_FALLBACK_MODEL)

    def test_generate_returns_body(self):
        client = FakeOpenAIClient({"*": VALID_BODY})
        result = generator_module.generate_comment_for_post(SAMPLE_POST, client=client)
        self.assertIsNotNone(result)
        self.assertIn("caching", result["body"])
        self.assertIsNotNone(result["ai_model"])

    def test_generate_rejects_image_markdown(self):
        client = FakeOpenAIClient({"*": VALID_BODY + " ![x](http://e.com/i.png)"})
        self.assertIsNone(generator_module.generate_comment_for_post(SAMPLE_POST, client=client))
    def test_generate_short_body_returns_none(self):
        client = FakeOpenAIClient({"*": "way too short"})
        self.assertIsNone(generator_module.generate_comment_for_post(SAMPLE_POST, client=client))

    def test_insufficient_credits_raises_status_code(self):
        err = Exception("Error code: 402 - {'error': {'message': 'Insufficient credits.'}}")
        err.status_code = 402
        client = FakeOpenAIClient({"*": err})
        with self.assertRaises(generator_module.InsufficientCredits) as ctx:
            generator_module.score_post(SAMPLE_POST, client=client)
        self.assertIn("402", str(ctx.exception))

    def test_insufficient_credits_detected_by_message(self):
        client = FakeOpenAIClient(
            {"*": Exception("You requested up to 600 tokens, but can only afford 352")}
        )
        with self.assertRaises(generator_module.InsufficientCredits) as ctx:
            generator_module.generate_comment_for_post(SAMPLE_POST, client=client)
        self.assertIn("afford", str(ctx.exception))

    def test_plain_error_does_not_raise_credits(self):
        client = FakeOpenAIClient({"*": Exception("Provider returned error")})
        score, reason, model = generator_module.score_post(SAMPLE_POST, client=client)
        self.assertEqual(score, 0.0)
        self.assertIsNone(model)


class CommentPersistenceTests(unittest.TestCase):
    def test_save_inserts_validated_row(self):
        client = FakeClient([{"id": "c1"}])
        self.assertTrue(persistence_module.save_comment(client, "p1", VALID_BODY, ai_model="m"))
        table, calls = client.queries[0]
        self.assertEqual(table, "comments")
        payload = calls[0][1][0]
        self.assertEqual(payload["post_id"], "p1")
        self.assertEqual(payload["author_type"], "ai")
        self.assertEqual(payload["status"], "approved")

    def test_save_dry_run_skips_insert(self):
        client = FakeClient([{"id": "c1"}])
        self.assertTrue(
            persistence_module.save_comment(client, "p1", VALID_BODY, dry_run=True)
        )
        self.assertEqual(client.queries, [])

    def test_save_rejects_invalid_body(self):
        client = FakeClient([{"id": "c1"}])
        self.assertFalse(persistence_module.save_comment(client, "p1", "short"))
        self.assertEqual(client.queries, [])


class CommentRunnerTests(unittest.TestCase):
    def setUp(self):
        self._orig = (
            runner_module.score_post,
            runner_module.generate_comment_for_post,
            runner_module.save_comment,
            runner_module.process_post,
        )
        self.addCleanup(self._restore)

    def _restore(self):
        (
            runner_module.score_post,
            runner_module.generate_comment_for_post,
            runner_module.save_comment,
            runner_module.process_post,
        ) = self._orig

    def test_process_post_comments_when_worthy(self):
        runner_module.score_post = lambda post: (8.5, "tradeoff", "m")
        runner_module.generate_comment_for_post = lambda post: {"body": VALID_BODY, "ai_model": "m"}
        runner_module.save_comment = lambda *a, **k: True
        client = FakeClient([])
        self.assertEqual(runner_module.process_post(client, SAMPLE_POST), "commented")

    def test_process_post_skips_existing(self):
        client = FakeClient([{"id": "c1"}])
        self.assertEqual(runner_module.process_post(client, SAMPLE_POST), "skipped_exists")

    def test_process_post_skips_prefetched_id_without_scoring(self):
        def _boom(post):
            raise AssertionError("scoring must not run for prefetched ids")

        runner_module.score_post = _boom
        client = FakeClient([])
        self.assertEqual(
            runner_module.process_post(client, SAMPLE_POST, {"p1"}), "skipped_exists"
        )

    def test_process_post_skips_low_score(self):
        runner_module.score_post = lambda post: (3.0, "meh", "m")
        client = FakeClient([])
        self.assertEqual(runner_module.process_post(client, SAMPLE_POST), "skipped_score")

    def test_process_post_failed_generate(self):
        runner_module.score_post = lambda post: (9.0, "great", "m")
        runner_module.generate_comment_for_post = lambda post: None
        client = FakeClient([])
        self.assertEqual(runner_module.process_post(client, SAMPLE_POST), "failed_generate")

    def test_process_post_propagates_insufficient_credits(self):
        def _broke(post):
            raise generator_module.InsufficientCredits("402 out of credits")

        runner_module.score_post = _broke
        client = FakeClient([])
        with self.assertRaises(generator_module.InsufficientCredits):
            runner_module.process_post(client, SAMPLE_POST)

    def test_run_loop_breaks_after_consecutive_errors(self):
        calls = []

        def _fail(client, post, commented_ids=None):
            calls.append(post["id"])
            return "failed_generate"

        runner_module.process_post = _fail
        client = FakeClient([])
        posts = [{"id": f"p{i}"} for i in range(5)]
        with mock.patch.object(runner_module.time, "sleep"):
            stats = runner_module.run_loop(client, posts)
        self.assertEqual(len(calls), 3)
        self.assertEqual(stats.get("failed_generate"), 3)

    def test_run_loop_skips_do_not_trip_breaker(self):
        outcomes = ["skipped_score", "failed_generate", "skipped_score", "commented"]

        def _mixed(client, post, commented_ids=None):
            return outcomes.pop(0)

        runner_module.process_post = _mixed
        client = FakeClient([])
        posts = [{"id": f"p{i}"} for i in range(4)]
        with mock.patch.object(runner_module.time, "sleep"):
            stats = runner_module.run_loop(client, posts)
        self.assertEqual(stats.get("commented"), 1)
        self.assertEqual(stats.get("skipped_score"), 2)


if __name__ == "__main__":
    unittest.main()
