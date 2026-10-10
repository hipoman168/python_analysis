-- DAYONG AgentOS v0.1 durable control plane. Apply only to a verified AgentOS Supabase project.
create schema if not exists agentos;
create table if not exists agentos.jobs (
 task_id text primary key,
 node_id text not null check (node_id ~ '^node-[0-9]+$'),
 skill text not null,
 status text not null default 'PENDING' check (status in ('PENDING','CLAIMED','COMPLETED','FAILED')),
 created_at timestamptz not null default now(),
 claimed_at timestamptz,
 finished_at timestamptz
);
create index if not exists jobs_claim_idx on agentos.jobs(node_id,created_at) where status='PENDING';
create table if not exists agentos.evidence (
 task_id text primary key references agentos.jobs(task_id),
 node_id text not null,
 canonical_payload jsonb not null,
 sha256 char(64) not null check (sha256 ~ '^[0-9a-f]{64}$'),
 received_at timestamptz not null default now()
);
create table if not exists agentos.events (
 id bigint generated always as identity primary key,
 task_id text not null references agentos.jobs(task_id),
 event_type text not null,
 recorded_at timestamptz not null default now(),
 detail jsonb not null default '{}'::jsonb
);
create index if not exists events_task_idx on agentos.events(task_id,recorded_at);
revoke all on schema agentos from anon, authenticated;
revoke all on all tables in schema agentos from anon, authenticated;
-- No public policies. Server-side service credentials only, with explicit authorization.
