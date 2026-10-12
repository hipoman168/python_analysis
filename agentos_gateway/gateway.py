"""DAYONG AgentOS Outbound Gateway v0.0.7 (final)."""
import os
import json
import sqlite3
import hashlib
import secrets
from typing import Optional, Literal
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="DAYONG AgentOS Outbound Gateway", version="0.0.7")

DB = os.getenv("GATEWAY_DB", "./gateway.db")
NODE_TOKEN = os.getenv("NODE_TOKEN")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
D2_READ_TOKEN = os.getenv("D2_READ_TOKEN")

SkillT = Literal["system_info", "agentos_development"]

ALLOWED_PAYLOAD_KEYS = {
    "branch", "base", "test_name", "commit_msg",
    "pr_title", "pr_body", "files", "work_dir",
}
FORBIDDEN_PAYLOAD_KEYS = {"repo_url", "test_cmd", "raw_cmd", "shell", "argv"}


def _init_db() -> None:
    with sqlite3.connect(DB) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                task_id      TEXT PRIMARY KEY,
                node_id      TEXT NOT NULL,
                skill        TEXT NOT NULL,
                payload_json TEXT,
                status       TEXT NOT NULL DEFAULT 'PENDING',
                evidence     TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cols = [r[1] for r in c.execute("PRAGMA table_info(jobs)").fetchall()]
        if "payload_json" not in cols:
            c.execute("ALTER TABLE jobs ADD COLUMN payload_json TEXT")


_init_db()


def _auth(header: Optional[str], expected: Optional[str]) -> None:
    if not expected:
        raise HTTPException(500, "Gateway token not configured")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = header[len("Bearer "):].strip()
    if not secrets.compare_digest(token, expected):
        raise HTTPException(403, "Invalid token")


def _auth_any(header: Optional[str], tokens) -> None:
    tokens = [t for t in tokens if t]
    if not tokens:
        raise HTTPException(500, "Gateway read tokens not configured")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = header[len("Bearer "):].strip()
    if not any(secrets.compare_digest(token, t) for t in tokens):
        raise HTTPException(403, "Invalid token")


class Job(BaseModel):
    task_id: str = Field(min_length=1)
    node_id: str = "node-02"
    skill: SkillT = "system_info"
    payload_json: Optional[str] = None


class Result(BaseModel):
    task_id: str
    status: str
    evidence: dict


def _validate_payload(payload_json: Optional[str]) -> None:
    if not payload_json:
        return
    try:
        p = json.loads(payload_json)
    except Exception as e:
        raise HTTPException(400, f"payload_json not valid JSON: {e}")
    if not isinstance(p, dict):
        raise HTTPException(400, "payload_json must be an object")
    unknown = set(p.keys()) - ALLOWED_PAYLOAD_KEYS
    if unknown:
        raise HTTPException(400, f"payload contains unknown keys: {sorted(unknown)}")
    bad = set(p.keys()) & FORBIDDEN_PAYLOAD_KEYS
    if bad:
        raise HTTPException(400, f"payload contains forbidden keys: {sorted(bad)}")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.0.7"}


@app.post("/v1/jobs")
def create_job(job: Job, authorization: Optional[str] = Header(None)):
    _auth(authorization, ADMIN_TOKEN)
    _validate_payload(job.payload_json)
    with sqlite3.connect(DB) as c:
        c.execute("BEGIN IMMEDIATE")
        if job.skill == "agentos_development":
            busy = c.execute(
                "SELECT COUNT(*) FROM jobs WHERE node_id=? AND status='CLAIMED'",
                (job.node_id,),
            ).fetchone()[0]
            if busy:
                raise HTTPException(409, "node already has a claimed job")
        exists = c.execute(
            "SELECT 1 FROM jobs WHERE task_id=?", (job.task_id,)
        ).fetchone()
        if exists:
            raise HTTPException(409, f"task_id already exists: {job.task_id}")
        c.execute(
            "INSERT INTO jobs (task_id, node_id, skill, payload_json, status) "
            "VALUES (?, ?, ?, ?, 'PENDING')",
            (job.task_id, job.node_id, job.skill, job.payload_json),
        )
    return {"task_id": job.task_id, "node_id": job.node_id,
            "skill": job.skill, "status": "PENDING"}


@app.post("/v1/nodes/{node_id}/claim")
def claim(node_id: str, authorization: Optional[str] = Header(None)):
    _auth(authorization, NODE_TOKEN)
    row = None
    with sqlite3.connect(DB) as c:
        c.execute("BEGIN IMMEDIATE")
        busy = c.execute(
            "SELECT task_id FROM jobs WHERE node_id=? AND status='CLAIMED' LIMIT 1",
            (node_id,),
        ).fetchone()
        if busy:
            c.execute("COMMIT")
            return {"task_id": None, "reason": "node_already_claimed",
                    "claimed_task_id": busy[0]}
        row = c.execute(
            "SELECT task_id, skill, payload_json FROM jobs "
            "WHERE node_id=? AND status='PENDING' "
            "ORDER BY created_at LIMIT 1",
            (node_id,),
        ).fetchone()
        if row:
            cur = c.execute(
                "UPDATE jobs SET status='CLAIMED' "
                "WHERE task_id=? AND status='PENDING'",
                (row[0],),
            )
            if cur.rowcount != 1:
                c.execute("ROLLBACK")
                raise HTTPException(409, "race: task not claimable")
        c.execute("COMMIT")
    if not row:
        return {"task_id": None}
    return {"task_id": row[0], "skill": row[1], "payload_json": row[2]}


@app.post("/v1/nodes/{node_id}/result")
def submit_result(node_id: str, result: Result, authorization: Optional[str] = Header(None)):
    _auth(authorization, NODE_TOKEN)
    e = result.evidence
    payload = e.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(400, "evidence.payload missing")
    if payload.get("task_id") != result.task_id:
        raise HTTPException(400, "Evidence identity mismatch: task_id")
    if payload.get("node_id") != node_id:
        raise HTTPException(400, "Evidence identity mismatch: node_id")
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode()
    ).hexdigest()
    if not secrets.compare_digest(digest, str(e.get("sha256", ""))):
        raise HTTPException(400, "Evidence hash mismatch")
    final = "COMPLETED" if result.status == "PASS" else "FAILED"
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "UPDATE jobs SET status=?, evidence=? "
            "WHERE task_id=? AND node_id=? AND status='CLAIMED'",
            (final, json.dumps(e, ensure_ascii=False),
             result.task_id, node_id),
        )
        if not cur.rowcount:
            raise HTTPException(409, "Task not claimed")
    return {"task_id": result.task_id, "status": final, "sha256": digest}


@app.get("/v1/jobs/{task_id}")
def get_job(task_id: str, authorization: Optional[str] = Header(None)):
    _auth_any(authorization, [ADMIN_TOKEN, D2_READ_TOKEN])
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT task_id, node_id, skill, status, created_at, payload_json "
            "FROM jobs WHERE task_id=?",
            (task_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "task not found")
    return {"task_id": row[0], "node_id": row[1], "skill": row[2],
            "status": row[3], "created_at": row[4], "payload_json": row[5]}


@app.get("/v1/jobs/{task_id}/evidence")
def get_evidence(task_id: str, authorization: Optional[str] = Header(None)):
    _auth_any(authorization, [ADMIN_TOKEN, D2_READ_TOKEN])
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT evidence FROM jobs WHERE task_id=?", (task_id,)
        ).fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "evidence not found")
    return json.loads(row[0])
