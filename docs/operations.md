# Operations

## Supabase Database Changes & Types

When you make changes to the database schema directly on the Supabase website dashboard, you must synchronize those changes back to the codebase.

1. **Update `infra/supabase/schema.sql`** to reflect the new state of your database.
2. **Regenerate TypeScript Types:**
   - Go to your Supabase project dashboard, click "Project Settings" -> "General" and find your "Project ID" (it's the 20-character string in your project URL).
   - Generate a Personal Access Token in your Supabase account settings.
   - Run the following command from the `apps/web` directory:
     ```bash
     export SUPABASE_PROJECT_ID="your_project_id"
     export SUPABASE_ACCESS_TOKEN="your_access_token"
     npm run generate-types
     ```
   - This will update `apps/web/src/lib/database.types.ts`.

## Scheduled Ingestion

The ingestion worker is run by `.github/workflows/ingest.yml`. The workflow installs Python dependencies, checks RSS feed availability, and runs the worker entrypoint.

Required secrets (OpenRouter-only generation):

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `OPEN_ROUTER_API_KEY`

Optional secrets configure markdown image behavior and image verification:

- `STRIP_MARKDOWN_IMAGES` — inline publisher images are stripped by default
  (replaced with a link back to the original article) to avoid copyright and
  hotlinking risk. Stripping stays ON unless explicitly set to `0`/`false`/
  `no`/`off`; an unset secret still strips. Set `STRIP_MARKDOWN_IMAGES=0`
  only when embeds are licensed or explicitly allowed.
- `ALLOW_INLINE_IMAGE_DOMAINS`
- `VERIFY_INLINE_IMAGES`
- `IMAGE_URL_CHECK_TIMEOUT_SECONDS`

Cover images are intentionally disabled: new posts are written with
`cover_image=None` (no external hotlinks, no licensing ambiguity). The
`posts.cover_image` column stays nullable so old rows keep working; to null
existing covers run
`python services/ingest/scripts/backfill_remove_covers.py --dry-run` first,
then without `--dry-run`. To strip inline images on existing rows, use
`scripts/backfill_inline_image_attribution.py` the same way.

Optional secrets override the OpenRouter model chain (defaults: DeepSeek V4
Flash 0731 primary, GLM 5.3 Flash fallback):

- `OPENROUTER_PRIMARY_MODEL`
- `OPENROUTER_FALLBACK_MODEL`

## Reading generation warnings

Per-item AI failures are retried automatically (fallback model, then whole-item
retry), so occasional warnings in a green run are normal and need no action
when `pipeline_summary` shows `new_posts_saved` matching `candidates`. The two
common warnings and what they mean:

- `Failed to parse JSON response` (+ `Response preview` line): the model
  returned non-JSON output (prose wrapping, bad escapes, or truncation at
  `AI_MAX_TOKENS`). The 500-char preview shows which. Occasional hits are
  sampling noise; frequent hits across many items suggest the prompt or token
  limit needs attention.
- `Empty model response (finish_reason=...)`: the provider returned no
  content — a content-filter refusal (check the `refusal=` snippet; security /
  offensive-tech stories trip this most) or an upstream hiccup. Retries
  usually pass. If one topic angle refuses repeatedly, consider whether the
  story fits the AI/SWE scope before forcing it through.

Act only when warnings cluster: repeated `failed_ai` / `failed_validation` in
`pipeline_summary`, or the same item exhausting all retries.

## RSS Health

`.github/workflows/rss-health.yml` validates configured RSS endpoints. It should run when feed definitions or RSS checking scripts change, and on a recurring schedule.

Failure policy in `services/ingest/scripts/check_rss_feeds.py`: transient errors (HTTP 429/5xx, timeouts, connection/DNS errors) are retried 3x with backoff; permanent errors (other 4xx like 404/410) fail fast. Any feed still failing exits 1 so dead feeds stay visible — fix the URL or remove the feed rather than ignoring red runs.

## Runtime Notes

- The ingest worker should use a Supabase service role key because it writes posts, tags, and audit records.
- The web app should use the Supabase anon key for public reads.
- Middleware rate limiting in the web app is in-memory and best treated as a lightweight guard, not a distributed production rate limiter.
- GitHub Actions is sufficient for scheduled publishing at the current scale. If ingestion volume grows, move the worker to a queue or scheduler designed for long-running jobs.

## Pending admin permission migration

Before applying 0005, inspect live grants, role memberships, table ownership, and existing policies/RPC functions; reconcile differences with the local contract. Use separate staging data first. Verify anon and non-admin authenticated Data API reads/writes, published-post/tag/approved-comment reads, service-role worker access, and admin transactions. Do not grant the restricted group to `authenticated`, `anon`, or the Data API authenticator. Create its database LOGIN credential only in a provider/ignored secret store.

Regenerate database types from the verified staging project after applying the migration with the documented generate-types command. Permissions do not change DTO columns, but regeneration remains pending until an authenticated staging target is available. Production application and rollback require the owner's concrete cutover review; keep the old backend running.


## OpenRouter credit checks before ingestion

News ingestion checks live credits before processing each candidate. It reads
`GET /api/v1/credits` with a management key and `GET /api/v1/key` with the
existing generation key. Usable USD is the smallest of the account balance
(`total_credits - total_usage`), the key's remaining allowance when capped,
and the effective budget when present. An uncapped key does not bypass the
account balance check.

Setup:

1. Create an OpenRouter management key and store it as the GitHub Actions
   repository secret `OPENROUTER_MANAGEMENT_API_KEY`. Keep the existing
   `OPEN_ROUTER_API_KEY` for model calls. For local runs, set both in
   `services/ingest/.env`.
2. Optionally set the repository variable `OPENROUTER_MIN_CREDITS_USD`
   (or the local environment variable). It defaults to `$0.05` and must be
   finite and positive. This floor is intended to cover an item's
   generation/fallback/retry calls and a reserve, rather than an exact cost
   estimate. Increase it for more expensive models or larger requests.

If usable credits fall below the floor, ingestion stops with summary note
`insufficient_credits`. Generated posts waiting for batch insertion are still
saved. A missing management key, API error, timeout, or invalid response stops
processing with `credit_check_failed`; an empty run then fails the job so the
problem is visible. Partial runs retain their existing success policy and
include the stop reason in the GitHub Actions summary.

Preflight does not reserve funds; other jobs (including AI comments) can spend
credits concurrently. An HTTP 402 during generation stops fallback attempts,
item retries, and subsequent items, while preserving completed posts. Rerun
after adding credits, raising the key/budget cap, or resolving transient
in-flight spending limits. These checks apply to news ingestion; the separate
AI comments job retains its existing behavior.

References: [credits endpoint](https://openrouter.ai/docs/api/api-reference/credits/get-remaining-credits)
and [key limits](https://openrouter.ai/docs/api_reference/limits).
