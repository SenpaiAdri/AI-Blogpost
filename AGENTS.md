# AGENTS.md

## Repo Structure

```
apps/web/          # Next.js 16 public site (React 19, Tailwind 4, TypeScript)
services/ingest/   # Python 3 ingestion worker (RSS -> AI generation -> Supabase)
infra/supabase/    # DB contract: schema.sql, migrations/, seed.sql
.github/workflows/ # Scheduled CI: ingest (2x daily cron) + RSS health
docs/              # architecture.md, operations.md, local-development.md
```

Each of these directories has its own `AGENTS.md` with detailed rules — they apply automatically when working there.

## Developer Commands

```bash
# Web app (run from apps/web/)
npm run dev             # dev server on :3000
npm run lint            # ESLint
npm run typecheck       # tsc --noEmit
npm run generate-types  # regenerates src/lib/database.types.ts from Supabase (needs SUPABASE_PROJECT_ID)

# Ingest worker (run from services/ingest/)
pip install -r requirements.txt
python src/main.py                  # full ingest pipeline
python -m unittest discover tests   # unit tests (fast, no external services needed)
python scripts/check_rss_feeds.py   # RSS health check (also run by CI)
```

## Key Constraints

- **Next.js 16: page `params` are Promises.** Type them as `params: Promise<{ slug: string }>` and `await` them (see `apps/web/src/app/blog/[slug]/page.tsx`).
- **Supabase is the only integration boundary.** Web app reads with the anon key (RLS applies); worker writes with the service role key. Never add direct HTTP calls between the two services.
- **Two Supabase clients** in `apps/web/src/lib/supabase.ts`: `supabase` (anon) vs `supabaseAdmin` (service key, bypasses RLS — server/API routes only).
- **Rate limiting** for `/api` and `/blog` paths lives in `apps/web/middleware.ts`, configured via `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_MS`.
- **Custom dark theme** — CSS variables in `globals.css` (#131316 background, plus #393A41 / #6A6B70 / #9A9BA2), not Tailwind defaults. Borders: `border-[#393A41] border-dashed`.

## Cross-File Sync Rules (easy to miss)

- Adding an env var to the Python worker -> also add it to the `env:` block of `.github/workflows/ingest.yml`, or the scheduled job won't receive it.
- Changing `infra/supabase/schema.sql` or adding a migration -> update `apps/web/src/lib/types.ts` AND `services/ingest/src/infra/database.py`, then regenerate `database.types.ts`.
- Major system/architecture/deployment changes -> update the relevant doc in `docs/`.

## Conventions

- Server Components fetch Supabase data directly (no separate API client import); interactive components need `"use client"`.
- Skeleton loaders are Suspense fallbacks (not just `loading.tsx`); infinite scroll uses IntersectionObserver (see `PostFeed.tsx`).
- Ingest worker: validate all AI output through `models.PostInsertModel` before DB insert; dedupe URLs against existing records before processing.
- Outbound fetches must go through SSRF protection (`services/ingest/src/safety/url_validation.py`) and respect per-host RPS limits (`services/ingest/src/infra/rate_limit.py`).

## Env Setup

```bash
cp .env.example apps/web/.env.local                   # anon key + rate limit vars
cp services/ingest/.env.example services/ingest/.env  # service key + AI keys
```

## Gotchas

- The ingest worker is not a long-running server: GitHub Actions triggers it twice daily (`0 0,12 * * *` UTC) or via manual dispatch. CI pins Python 3.12.
- Worker needs `SUPABASE_SERVICE_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`) — the anon key cannot write.
