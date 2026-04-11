create extension if not exists pgcrypto;

create table if not exists public.ai_generation_logs (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    topic text not null,
    source_name text not null,
    source_url text not null,
    status text not null,
    selected_model text,
    failure_reason text,
    output_json jsonb,
    validated boolean not null default false
);

create index if not exists idx_ai_generation_logs_created_at
    on public.ai_generation_logs (created_at desc);

create index if not exists idx_ai_generation_logs_status
    on public.ai_generation_logs (status);

create index if not exists idx_ai_generation_logs_source_url
    on public.ai_generation_logs (source_url);
