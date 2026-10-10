# DAYONG AgentOS v0.1.0 — AI Workforce API Contract

Status: DRAFT. No deployment or end-to-end verification claimed.

## Roles and access
- CEO: task administration, assignments, reviews.
- D1: assigned-task read/write and meeting participation.
- D2: assigned-task read/write, evidence retrieval, review signoff.
- Node Worker: claim and submit only for its own node.
- Every principal uses its own revocable credential. Never distribute ADMIN_TOKEN to agents.

## Proposed routes
- GET /v1/me — principal identity and scopes.
- GET /v1/tasks?status=... — list tasks visible to principal.
- POST /v1/tasks — create a task, subject to scope.
- GET /v1/tasks/{task_id} — read a permitted task.
- POST /v1/tasks/{task_id}/claim — atomic lease with expiry.
- POST /v1/tasks/{task_id}/events — append status/progress.
- POST /v1/tasks/{task_id}/complete — submit outcome and evidence reference.
- GET /v1/tasks/{task_id}/evidence — authenticated original evidence retrieval.
- GET /v1/meetings — list accessible meetings.
- POST /v1/meetings/{meeting_id}/contributions — record agent input.
- GET /v1/events?cursor=... — resumable event feed; use backoff, not high-frequency polling.

## Persistence
Use durable Postgres for tasks, leases, events, and audit log, and durable object storage for original Evidence blobs. Store SHA256, byte size, provenance, timestamps, and immutable evidence identifiers. Do not migrate/restart the existing SQLite gateway until old data is exported and independently verified.

## Safety and acceptance
1. Cross-agent and cross-node authorization denied by default.
2. Tokens scoped, rotated, revocable, and never logged.
3. Duplicate submissions are idempotent; claims have expirations.
4. Original Evidence round-trips byte-for-byte and verifies SHA256.
5. Restart does not lose tasks, events, or Evidence.
6. Agent can retrieve assigned work, submit result, and review Evidence without chairman intervention.
7. Audit records identify actor, action, task, timestamp, and outcome.
8. No PASS status without observed deployment and test evidence.

## Rollout
Phase A: non-destructive API and storage tests on staging.
Phase B: migrate and verify old SQLite records before production cutover.
Phase C: D1/D2 scoped credential provisioning and real task/meeting integration.
