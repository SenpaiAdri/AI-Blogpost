-- AI comments contract (Phase 0).
-- Generic comments table: AI-only writes in v1, future-proof for human replies.
-- Public reads only approved rows; writes via service_role / supabaseAdmin.

create table if not exists public.comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts(id) on delete cascade,
  parent_id uuid references public.comments(id) on delete cascade,
  author_type text not null check (author_type in ('human', 'ai', 'anonymous')),
  author_name text,
  author_user_id text,
  body text not null check (char_length(body) between 1 and 5000),
  ai_model text,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'rejected', 'spam')),
  moderated_by text,
  moderated_at timestamptz,
  created_at timestamptz not null default now(),
  constraint comments_moderation_consistent check (
    (status = 'pending' and moderated_by is null and moderated_at is null)
    or (status in ('approved', 'rejected', 'spam'))
  )
);

comment on table public.comments is
  'Human/AI comments on posts. Public reads only approved rows; writes moderated via status.';

create index if not exists comments_post_created_idx
  on public.comments (post_id, created_at desc)
  where status = 'approved';

create index if not exists comments_parent_id_idx
  on public.comments (parent_id);

create index if not exists comments_status_created_idx
  on public.comments (status, created_at desc);

-- First RLS in repo: anon key is public, so enforce approved-only reads at DB level.
alter table public.comments enable row level security;

drop policy if exists comments_read_approved on public.comments;

create policy comments_read_approved on public.comments
  for select to anon using (status = 'approved');
