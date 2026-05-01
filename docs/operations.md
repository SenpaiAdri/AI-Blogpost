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

Required secrets:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GOOGLE_API_KEY`
- `OPEN_ROUTER_API_KEY`

Optional secrets configure markdown image behavior and image verification:

- `STRIP_MARKDOWN_IMAGES`
- `ALLOW_INLINE_IMAGE_DOMAINS`
- `VERIFY_INLINE_IMAGES`
- `IMAGE_URL_CHECK_TIMEOUT_SECONDS`

## RSS Health

`.github/workflows/rss-health.yml` validates configured RSS endpoints. It should run when feed definitions or RSS checking scripts change, and on a recurring schedule.

## Runtime Notes

- The ingest worker should use a Supabase service role key because it writes posts, tags, and audit records.
- The web app should use the Supabase anon key for public reads.
- Middleware rate limiting in the web app is in-memory and best treated as a lightweight guard, not a distributed production rate limiter.
- GitHub Actions is sufficient for scheduled publishing at the current scale. If ingestion volume grows, move the worker to a queue or scheduler designed for long-running jobs.
