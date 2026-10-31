-- Admin migration permission contract. Review effective live grants/memberships first.
-- Apply to disposable local/staging data before any separately approved production cutover.
-- Provision a LOGIN role with a secret outside source control and grant it aiblogpost_admin.
BEGIN;
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aiblogpost_admin') THEN
    CREATE ROLE aiblogpost_admin NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname='aiblogpost_admin' AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolcanlogin)) THEN
    RAISE EXCEPTION 'aiblogpost_admin must be an unprivileged NOLOGIN group role';
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO aiblogpost_admin, anon, authenticated, service_role;
REVOKE ALL ON public.posts, public.tags, public.post_tags, public.comments,
  public.ai_generation_logs, public.post_moderation_events, public.topic_guidance, public.rss_sources
  FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.posts, public.tags, public.post_tags, public.comments TO anon, authenticated;
GRANT ALL ON public.posts, public.tags, public.post_tags, public.comments,
  public.ai_generation_logs, public.post_moderation_events, public.topic_guidance, public.rss_sources TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.tags_id_seq TO service_role;

GRANT SELECT ON public.posts, public.ai_generation_logs, public.post_moderation_events, public.topic_guidance, public.rss_sources TO aiblogpost_admin;
GRANT UPDATE (is_published) ON public.posts TO aiblogpost_admin;
GRANT INSERT (post_id, action, reason, previous_is_published, new_is_published, created_by) ON public.post_moderation_events TO aiblogpost_admin;
GRANT INSERT (keyword, normalized_keyword, weight, status, expires_at, created_by) ON public.topic_guidance TO aiblogpost_admin;
GRANT UPDATE (status, deactivated_by, deactivated_at) ON public.topic_guidance TO aiblogpost_admin;
GRANT INSERT (name, url) ON public.rss_sources TO aiblogpost_admin;
GRANT UPDATE (is_active) ON public.rss_sources TO aiblogpost_admin;

ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON public.posts;
CREATE POLICY public_read ON public.posts AS PERMISSIVE FOR SELECT TO anon, authenticated USING (is_published = true);
DROP POLICY IF EXISTS public_read_boundary ON public.posts;
CREATE POLICY public_read_boundary ON public.posts AS RESTRICTIVE FOR SELECT TO anon, authenticated USING (is_published = true);
ALTER TABLE public.tags ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON public.tags;
CREATE POLICY public_read ON public.tags AS PERMISSIVE FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS public_read_boundary ON public.tags;
CREATE POLICY public_read_boundary ON public.tags AS RESTRICTIVE FOR SELECT TO anon, authenticated USING (true);
ALTER TABLE public.post_tags ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON public.post_tags;
CREATE POLICY public_read ON public.post_tags AS PERMISSIVE FOR SELECT TO anon, authenticated USING (EXISTS (SELECT 1 FROM public.posts p WHERE p.id = post_id AND p.is_published));
DROP POLICY IF EXISTS public_read_boundary ON public.post_tags;
CREATE POLICY public_read_boundary ON public.post_tags AS RESTRICTIVE FOR SELECT TO anon, authenticated USING (EXISTS (SELECT 1 FROM public.posts p WHERE p.id = post_id AND p.is_published));
ALTER TABLE public.comments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_read ON public.comments;
CREATE POLICY public_read ON public.comments AS PERMISSIVE FOR SELECT TO anon, authenticated USING (status = 'approved' AND EXISTS (SELECT 1 FROM public.posts p WHERE p.id = post_id AND p.is_published));
DROP POLICY IF EXISTS public_read_boundary ON public.comments;
CREATE POLICY public_read_boundary ON public.comments AS RESTRICTIVE FOR SELECT TO anon, authenticated USING (status = 'approved' AND EXISTS (SELECT 1 FROM public.posts p WHERE p.id = post_id AND p.is_published));
ALTER TABLE public.ai_generation_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_deny ON public.ai_generation_logs;
CREATE POLICY public_deny ON public.ai_generation_logs AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
ALTER TABLE public.post_moderation_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_deny ON public.post_moderation_events;
CREATE POLICY public_deny ON public.post_moderation_events AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
ALTER TABLE public.topic_guidance ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_deny ON public.topic_guidance;
CREATE POLICY public_deny ON public.topic_guidance AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
ALTER TABLE public.rss_sources ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS public_deny ON public.rss_sources;
CREATE POLICY public_deny ON public.rss_sources AS RESTRICTIVE FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS admin_read ON public.posts;
CREATE POLICY admin_read ON public.posts FOR SELECT TO aiblogpost_admin USING (true);
DROP POLICY IF EXISTS admin_read ON public.ai_generation_logs;
CREATE POLICY admin_read ON public.ai_generation_logs FOR SELECT TO aiblogpost_admin USING (true);
DROP POLICY IF EXISTS admin_read ON public.post_moderation_events;
CREATE POLICY admin_read ON public.post_moderation_events FOR SELECT TO aiblogpost_admin USING (true);
DROP POLICY IF EXISTS admin_read ON public.topic_guidance;
CREATE POLICY admin_read ON public.topic_guidance FOR SELECT TO aiblogpost_admin USING (true);
DROP POLICY IF EXISTS admin_read ON public.rss_sources;
CREATE POLICY admin_read ON public.rss_sources FOR SELECT TO aiblogpost_admin USING (true);
DROP POLICY IF EXISTS admin_update ON public.posts;
CREATE POLICY admin_update ON public.posts FOR UPDATE TO aiblogpost_admin USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS admin_update ON public.topic_guidance;
CREATE POLICY admin_update ON public.topic_guidance FOR UPDATE TO aiblogpost_admin USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS admin_update ON public.rss_sources;
CREATE POLICY admin_update ON public.rss_sources FOR UPDATE TO aiblogpost_admin USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS admin_insert ON public.post_moderation_events;
CREATE POLICY admin_insert ON public.post_moderation_events FOR INSERT TO aiblogpost_admin WITH CHECK (true);
DROP POLICY IF EXISTS admin_insert ON public.topic_guidance;
CREATE POLICY admin_insert ON public.topic_guidance FOR INSERT TO aiblogpost_admin WITH CHECK (true);
DROP POLICY IF EXISTS admin_insert ON public.rss_sources;
CREATE POLICY admin_insert ON public.rss_sources FOR INSERT TO aiblogpost_admin WITH CHECK (true);
COMMIT;
