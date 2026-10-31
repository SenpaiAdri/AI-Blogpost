-- Match inspected production definitions; owner approved reconciliation on 2026-10-30.
-- These are contract corrections, not a request to change the working production database.
-- Apply to staging first. Unexpected NULL log sources fail rather than inventing data.
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.posts ALTER COLUMN is_published DROP NOT NULL;
ALTER TABLE public.ai_generation_logs ALTER COLUMN source_name SET NOT NULL;
ALTER TABLE public.ai_generation_logs ALTER COLUMN source_url SET NOT NULL;
ALTER TABLE public.tags DROP COLUMN IF EXISTS created_at;
ALTER TABLE public.post_tags DROP COLUMN IF EXISTS created_at;
