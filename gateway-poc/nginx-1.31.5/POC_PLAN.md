# NGINX 1.31.5 Gateway PoC Plan

## Goal
Validate NGINX 1.31.5 as a coarse content-aware routing layer in front of the DAYONG AI Factory MCP/API Gateway without replacing central authorization and governance.

## Governance Boundary
NGINX may perform only first-layer routing and coarse rejection based on parsed request content. Final authorization remains in the AI Factory control plane:

Agent Request -> NGINX Content-Aware Router -> Identity -> Role -> Permission -> Resource Scope -> Risk -> Approval Gate -> Tool/Runner -> Evidence -> Audit

Caller-provided values such as `risk_level=LOW` must never be treated as authoritative.

## Build Capability Gate
Before testing, verify the target binary is NGINX >= 1.31.5 and was built with:

- `--with-http_json_module`
- `--with-control-api`

Record `nginx -V` in Evidence. Do not continue if required modules are absent.

## Scope
PoC is limited to isolated JSON/MCP HTTP endpoints. Do not apply `client_body_early_read` globally and do not apply it to gRPC/unbuffered request-body paths.

## Test Matrix
1. Valid MCP `tools/call` request routes to allowlisted upstream.
2. Missing routing field is rejected or sent to safe default-deny path.
3. Malformed JSON is rejected.
4. JSON nesting above configured `json_max_depth` is rejected.
5. Request body above `client_max_body_size` is rejected before application execution.
6. Unknown `tool_name` is denied.
7. Content-aware rate limit is enforced before the protected application.
8. Control API is reachable only over a protected UNIX domain socket with restrictive file permissions.
9. Multiple extracted JSON fields from the same request are benchmarked to verify acceptable overhead.

## Required Evidence
- exact NGINX version and build flags
- config checksum
- request/response samples for all tests
- HTTP status for every negative test
- upstream selected for every positive test
- latency p50/p95 and throughput comparison against path-only routing baseline
- resource usage during benchmark
- Control API socket ownership/permissions
- logs proving denied requests did not reach protected upstream

## Acceptance Criteria
PoC passes only if:

- valid allowlisted MCP requests are routed correctly;
- malformed/oversize/deep/unknown-tool requests fail closed;
- Control API is not network exposed;
- no protected upstream receives a denied request;
- central Policy Gatekeeper remains the authorization authority;
- measured overhead is documented and judged acceptable for the target workload.

## Production Rule
Passing this PoC does not authorize production deployment. Production change requires a separate reviewed WorkOrder and Approval Gate.
