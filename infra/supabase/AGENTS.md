# Supabase Infrastructure - Agent Guidelines

## Role
Source of truth for the database schema, shared between the Next.js web application and the Python ingest worker.

## Key Files
- `schema.sql`: The current expected schema for the database.
- `migrations/`: Directory containing ordered migration scripts.
- `seed.sql`: Reserved for local development seed data.

## Security & Access Patterns
The system relies on Supabase acting as the integration boundary between the frontend and backend. 
- **Frontend (`apps/web`)**: Has **READ-ONLY** access to `posts`, `tags`, and `post_tags` tables using the public `anon` key.
- **Backend (`services/ingest`)**: Has **FULL READ/WRITE** access using the `service_role` key. It handles writing posts, tags, and AI generation audit rows.

## Important Constraints & Rules
- **Schema Alignment:** If you modify `schema.sql` or create a migration, you MUST ensure that the TypeScript types in `apps/web/src/lib/types.ts` and the Python data models/queries in `services/ingest/src/database.py` are updated accordingly to stay aligned.
- **No Direct Service Communication:** The web app and the Python worker never communicate directly via HTTP. They only interact via reading/writing to this Supabase schema.
