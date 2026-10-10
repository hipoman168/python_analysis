# DAYONG AgentOS — GitHub-first durable repository v0.1
Status: DESIGN / NOT DEPLOYED. This does not claim Node-01 or Node-02 connectivity.

## Role of GitHub
- Source of truth for source code, schemas, configuration templates and immutable, reviewable acceptance reports.
- Evidence files: store small, non-secret, redacted evidence in `agentos_gateway/evidence/<task_id>/` or GitHub Releases for larger immutable bundles, subject to GitHub limits.
- Preserve original evidence bytes as attachments; never reformat JSON before hashing. Store SHA256 manifest and source metadata.
- Never commit API keys, tokens, personally identifying data, internal IPs, or raw sensitive machine inventories.

## Runtime boundary
GitHub is not a continuously running inbound API host or low-latency message queue.
- Existing Render Gateway remains the active transport temporarily; DO NOT redeploy or restart before SQLite evidence backup.
- Node workers initiate outbound HTTPS to Gateway; GitHub Actions can run CI and controlled deployments, not act as 24/7 node polling.
- If later replacing Gateway, provision a separate HTTPS service and perform a cutover only after verified backup and node E2E.
- GitHub repository contents API should not be used for per-second polling; use event-driven or 4-hour default health checks when justified.

## Acceptance criteria
1. Node-01 and Node-02 each receive a fresh job through the live Gateway.
2. Both return a result and a durable, independently verifiable evidence bundle.
3. Original bytes, checksum, node identity and timestamps are preserved in GitHub.
4. Disconnect Desktop Commander and repeat; job transport still works.
5. Read-only D2 access verifies results without administrative credentials.
6. Old Render SQLite evidence recovered and hashed before any Render restart or deploy.

## Next implementation
Create a GitHub Actions CI job to run Gateway tests on push; create a redacted evidence manifest format; implement a least-privilege upload workflow with protected environment and explicit approvals for production deployment.
