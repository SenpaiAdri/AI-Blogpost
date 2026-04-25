# Supabase Contract

This folder owns the database contract shared by the web app and ingest worker.

- `schema.sql` is the current expected schema.
- `migrations/` is where ordered migration files should live.
- `seed.sql` is reserved for local seed data.

The web app reads from `posts`, `tags`, and `post_tags` using the public anon key. The ingest worker writes posts, tags, post-tag links, and AI audit rows with a Supabase service role key.
