-- Anon read access for AI comments (Phase 2 review fix).
-- 0003 created the table + RLS policy, but raw-SQL migrations get no
-- auto-grants, so anon reads failed with 42501 and the section rendered empty.

grant select on public.comments to anon;
