# Ingest Worker - Agent Guidelines

## Role
Python worker that fetches RSS feeds, scrapes articles, uses LLMs to generate blog posts, and writes data to Supabase.

## Key Files & Structure
- `src/main.py`: Main execution pipeline.
- `src/database.py`: Supabase database operations and queries.
- `src/generator.py`: AI generation logic (LLM integration).
- `src/ai_audit.py`: Audit logging for AI generations.
- `src/scraper.py` & `src/rss_feeds.py`: Data ingestion logic.
- `tests/`: Unit tests for the worker.

## Environment & Permissions
- **Database Access:** Requires `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_SERVICE_KEY`). It must use the service role key, not the anon key, as this worker handles trusted, privileged writes to the database.
- **AI Keys:** Requires `GOOGLE_API_KEY` or `OPEN_ROUTER_API_KEY` for generation.

## Developer Commands
- Run worker: `python src/main.py`
- Run tests: `python -m unittest discover tests`
- Install dependencies: `python -m pip install -r requirements.txt`

## Important Constraints & Rules
- **AI Output Validation:** AI outputs must always be validated (e.g., using `security.validate_ai_output`) before saving to the database.
- **Deduplication:** New URLs must be checked against existing records (using `database.get_all_existing_urls` or `database.check_duplicate_url`) before processing to prevent double-posting.
- **Integration Boundary:** Do not add code that attempts to communicate directly with the Next.js web application. Supabase acts as the sole integration boundary.
