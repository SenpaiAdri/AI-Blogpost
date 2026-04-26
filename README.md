## AI Blogpost

AI Blogpost is an autonomous tech-news publishing platform. It watches RSS feeds, filters for relevant technology stories, enriches each selected item with article context, asks an AI model to generate a concise source-backed blog post, and publishes the result to a Next.js site.

The project covers the broader technology landscape: AI, security, cloud, developer tools, platforms, hardware, and enterprise software. The "AI" in AI Blogpost describes the publishing engine as much as the topic focus.

## Architecture

This is a polyglot single repository, not a classic single-process monolith.

- `apps/web` contains the Next.js web app that reads published posts from Supabase.
- `services/ingest` contains the Python ingestion worker that fetches RSS feeds, generates posts, and writes them to Supabase.
- `infra/supabase` documents the database contract shared by both runtimes.
- `.github/workflows` runs scheduled ingestion and RSS health checks.

Supabase is the integration boundary between the web app and the ingest worker. The web app does not call the Python worker directly.

## AI Providers

The primary generation model is Gemini 2.5 Flash. The ingest worker also supports OpenRouter-compatible fallback models when configured.

## Local Development

Install and run the web app:

```bash
cd apps/web
npm install
npm run dev
```

Run the ingest worker:

```bash
cd services/ingest
python -m pip install -r requirements.txt
python src/main.py
```

Copy the example env files before running locally:

- Root/web env: `.env.example`
- Ingest worker env: `services/ingest/.env.example`

## Documentation

- `docs/architecture.md` explains the runtime boundaries and data flow.
- `docs/operations.md` explains scheduled ingestion and operational notes.
- `docs/local-development.md` explains local setup.
