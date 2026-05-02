-- Admin moderation and topic guidance contract.
-- Tables are written by the Spring Boot admin backend; topic_guidance is read by the ingest worker.

create table if not exists public.post_moderation_events (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts(id),
  action text not null check (action in ('UNPUBLISH')),
  reason text,
  previous_is_published boolean not null,
  new_is_published boolean not null,
  created_by text not null,
  created_at timestamptz not null default now()
);

comment on table public.post_moderation_events is
  'Admin-owned audit log for post visibility changes. Written by the Spring Boot admin backend.';

create table if not exists public.topic_guidance (
  id uuid primary key default gen_random_uuid(),
  keyword text not null,
  normalized_keyword text not null,
  weight integer not null default 1 check (weight between 1 and 5),
  status text not null default 'ACTIVE' check (status in ('ACTIVE', 'DEACTIVATED')),
  expires_at timestamptz not null,
  created_by text not null,
  created_at timestamptz not null default now(),
  deactivated_by text,
  deactivated_at timestamptz,
  constraint topic_guidance_keyword_length check (char_length(keyword) between 2 and 120),
  constraint topic_guidance_normalized_keyword_length check (char_length(normalized_keyword) between 2 and 120)
);

comment on table public.topic_guidance is
  'Admin-owned editorial guidance. Written by the Spring Boot admin backend and read by the Python ingestion worker.';

create index if not exists post_moderation_events_post_id_idx
  on public.post_moderation_events (post_id);

create index if not exists post_moderation_events_created_at_idx
  on public.post_moderation_events (created_at desc);

create index if not exists topic_guidance_active_idx
  on public.topic_guidance (status, expires_at);

create index if not exists topic_guidance_created_at_idx
  on public.topic_guidance (created_at desc);

create unique index if not exists topic_guidance_active_keyword_uidx
  on public.topic_guidance (normalized_keyword)
  where status = 'ACTIVE';
