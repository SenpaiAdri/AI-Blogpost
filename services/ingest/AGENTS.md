# Ingest Worker - Agent Guidelines

## Role
Python worker that fetches RSS feeds, scrapes articles, uses LLMs to generate blog posts, and writes data to Supabase.

## Key Files & Structure
- `src/main.py`: Thin CLI entrypoint (imports `pipeline.orchestrator:main`).
- `src/config.py`: Single source of truth for tunables/limits (import from here, don't redefine).
- `src/models.py`: Pydantic validation gate for AI output (`PostInsertModel`).
- `src/selection/`: Candidate selection — `models.py` (NewsItem/ActiveTopic), `rss_feeds.py` (registry), `feeds.py` (fetch/select), `relevance.py` (tiered filter), `dedupe.py`, `topics.py`, `scraper.py`.
- `src/generation/`: AI generation — `prompts.py`, `llm_client.py` (OpenRouter chain), `json_recovery.py`, `markdown.py` (fences/tables/sanitize), `images.py` (policy/attribution), `normalization.py` (validate/finalize/telemetry), `cover.py`.
- `src/pipeline/`: Orchestration — `orchestrator.py` (main run), `processor.py` (per-item flow), `persistence.py` (Supabase writes), `sources.py` (attribution), `formatting.py` (AI context), `run_stats.py` (summary).
- `src/safety/`: `url_validation.py` (SSRF), `sanitization.py`, `slugs.py`.
- `src/infra/`: `database.py` (Supabase client/queries), `ai_audit.py`, `metrics.py` (cost/budget), `rate_limit.py`, `logger.py`.
- `tests/`: Unit tests for the worker.
- `scripts/`: One-off ops (`check_rss_feeds.py`, `list_tags.py`, `backfill_*.py`).

## Environment & Permissions
- **Database Access:** Requires `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_SERVICE_KEY`). It must use the service role key, not the anon key, as this worker handles trusted, privileged writes to the database.
- **AI Keys:** Requires `OPEN_ROUTER_API_KEY` for generation (OpenRouter-only chain).

## Developer Commands
- Run worker: `python src/main.py`
- Run tests: `python -m unittest discover tests`
- Install dependencies: `python -m pip install -r requirements.txt`

## Important Constraints & Rules
- **AI Output Validation:** AI outputs must always be validated (using `models.PostInsertModel`) before saving to the database to ensure correct typing, structure, and SSRF protection via Pydantic.
- **Deduplication:** New URLs must be checked against existing records (using `infra.database.get_all_existing_urls` or `infra.database.check_duplicate_url`) before processing to prevent double-posting.
- **Config:** New tunables go in `src/config.py`; other modules import from there instead of `os.getenv` duplication or redefining limits.
- **Integration Boundary:** Do not add code that attempts to communicate directly with the Next.js web application. Supabase acts as the sole integration boundary.
