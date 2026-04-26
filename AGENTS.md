# AGENTS.md

## Repo Structure

```
apps/web/          # Next.js 16 web app (React 19, Tailwind 4, TypeScript)
services/ingest/  # Python 3 ingestion worker
infra/supabase/    # DB contract docs
.github/workflows/ # Scheduled CI: ingest + RSS health
docs/              # Architecture, ops, local-dev docs
```

## Developer Commands

```bash
# Web app
cd apps/web && npm run dev      # dev server on :3000
cd apps/web && npm run lint     # ESLint (no typecheck script)
cd apps/web && npx tsc --noEmit # TypeScript check

# Ingest worker
cd services/ingest
python -m pip install -r requirements.txt
python src/main.py            # run ingest
python -m unittest discover tests
```

## Key Constraints

- **No typecheck npm script** — use `npx tsc --noEmit` manually
- **Next.js uses v16** — supports async request APIs but NOT `params` promise (params are sync in v16)
- **Supabase is integration boundary** — web app reads from it, worker writes to it (no direct calls)
- **Rate limiting** — configured in `apps/web/middleware.ts` via `RATE_LIMIT_*` env vars
- **Dark theme (#131316)** — CSS variables in `globals.css`

## Patterns to Follow

- Server components fetch data directly (no API client import in server files)
- Client components marked with `"use client"` directive
- Skeleton loaders use Suspense with fallback
- Use IntersectionObserver for infinite scroll (see `PostFeed.tsx`)
- Tailwind border style: `border-[#393A41] border-dashed`

## Env Setup

```bash
cp .env.example apps/web/.env.local       # Next.js needs this
cp services/ingest/.env.example services/ingest/.env
```

## What Agents Commonly Miss

- Next.js v16 doesn't need `await params` — params are sync
- Skeleton components needed for Suspense fallback (not just loading.tsx)
- CSS uses custom colors (#131316, #393A41, #6A6B70, #9A9BA2) not Tailwind defaults
- Ingest worker runs separately from web app (not started via npm)