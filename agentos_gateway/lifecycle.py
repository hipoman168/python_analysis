"""Opt-in DAYONG AgentOS task lifecycle; conservative migration of v0.0.7 jobs.

Existing queued jobs, credentials, node worker routes, and old evidence remain
backward compatible. Strict HMAC/nonce applies only to auto_wake=True jobs.
No independent second queue: the existing gateway.jobs table is authoritative.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

GITHUB_REPO = "hipoman168/dayong-dev-center"
GITHUB_WORKFLOW = "dayong-agentos-cloud-claim.yml"
GITHUB_REF = "feature/command-bridge-v01"
MAX_ATTEMPTS = 3
CLAIM_TTL_SECONDS = 900


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def init_schema(connection: sqlite3.Connection) -> None:
    columns = {r[1] for r in connection.execute("PRAGMA table_info(jobs)")}
    additions = (
        ("nonce", "TEXT"),
        ("auto_wake", "INTEGER NOT NULL DEFAULT 0"),
        ("attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("claimed_at", "TEXT"),
        ("finished_at", "TEXT"),
        ("last_error", "TEXT"),
        ("dispatch_status", "TEXT"),
    )
    for key, dtype in additions:
        if key not in columns:
            connection.execute(f"ALTER TABLE jobs ADD COLUMN {key} {dtype}")
    connection.execute("""CREATE TABLE IF NOT EXISTS job_audit (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        old_state TEXT,
        new_state TEXT NOT NULL,
        reason TEXT NOT NULL,
        event_at TEXT NOT NULL,
        evidence_sha256 TEXT
    )""")
    connection.execute("CREATE INDEX IF NOT EXISTS job_audit_task_idx ON job_audit(task_id,audit_id)")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def audit(connection, task_id, previous, nxt, reason, evidence_sha=None):
    connection.execute(
        "INSERT INTO job_audit (task_id,old_state,new_state,reason,event_at,evidence_sha256)"
        " VALUES (?,?,?,?,?,?)",
        (task_id, previous, nxt, reason, utcnow(), evidence_sha),
    )


def reclaim_stale(connection: sqlite3.Connection) -> dict:
    """Must be called inside BEGIN IMMEDIATE before selecting next queued job."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=CLAIM_TTL_SECONDS)).isoformat()
    rows = connection.execute(
        "SELECT task_id,attempts FROM jobs WHERE status='CLAIMED' AND "
        "claimed_at IS NOT NULL AND claimed_at < ?", (cutoff,),
    ).fetchall()
    counters = {"retried": 0, "deadlettered": 0}
    for task_id, attempts in rows:
        if attempts >= MAX_ATTEMPTS:
            target, reason, key = "DEADLETTER", "claim_timeout_exhausted", "deadlettered"
        else:
            target, reason, key = "PENDING", "claim_timeout_retry", "retried"
        updated = connection.execute(
            "UPDATE jobs SET status=?, claimed_at=NULL,last_error=? "
            "WHERE task_id=? AND status='CLAIMED'",
            (target, reason, task_id),
        )
        if updated.rowcount:
            audit(connection, task_id, "CLAIMED", target, reason)
            counters[key] += 1
    return counters


def check_result_signature(evidence: dict, node_token: str, expected_nonce: str) -> bool:
    payload = evidence.get("payload")
    if not isinstance(payload, dict) or payload.get("nonce") != expected_nonce:
        return False
    given = evidence.get("hmac_sha256")
    if not isinstance(given, str) or len(given) != 64:
        return False
    expected = hmac.new(node_token.encode("utf-8"), canonical(payload), hashlib.sha256).hexdigest()
    return secrets.compare_digest(expected, given)


def dispatch_github(*, node_id: str, task_id: str) -> str:
    """Wake an exact node workflow; never include payload or any secret in inputs."""
    token = os.getenv("AGENTOS_GITHUB_WAKE_TOKEN")
    if not token:
        return "WAKE_TOKEN_MISSING"
    if node_id not in ("node-01", "node-02"):
        return "NODE_NOT_ALLOWLISTED"
    body = {"ref": GITHUB_REF, "inputs": {"node_id": node_id, "task_id": task_id}}
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    request = urllib.request.Request(url, data=canonical(body), method="POST", headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "DAYONG-AgentOS-Lifecycle/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return "WAKE_ACCEPTED" if response.status == 204 else "WAKE_HTTP_UNEXPECTED"
    except urllib.error.HTTPError as error:
        return "WAKE_HTTP_" + str(error.code)
    except (OSError, TimeoutError):
        return "WAKE_TRANSPORT_FAILED"
