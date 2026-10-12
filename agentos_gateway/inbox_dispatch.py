"""Atomic D2 inbox claim + verifiable result; separate from legacy jobs.

RECEIVED is delivery only. A claim is not execution. No automatic retries
for uncertain writes; a stuck claim requires operator reconciliation.
"""
import hashlib
import json
import os
import secrets
import sqlite3
from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .dual_channel import _auth, _db

router = APIRouter()


class InboxClaim(BaseModel):
    node_id: Literal["node-02"] = "node-02"


class InboxResult(BaseModel):
    node_id: Literal["node-02"] = "node-02"
    status: Literal["PASS", "FAIL", "BLOCKED"]
    evidence: dict = Field(min_length=1)


def _ensure(c: sqlite3.Connection):
    c.execute("""CREATE TABLE IF NOT EXISTS agent_inbox_claims (
        message_id TEXT PRIMARY KEY REFERENCES agent_inbox(message_id),
        node_id TEXT NOT NULL, claimed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS agent_inbox_evidence (
        message_id TEXT PRIMARY KEY REFERENCES agent_inbox(message_id),
        node_id TEXT NOT NULL, outcome TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        finished_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")


def _node_auth(authorization: Optional[str]):
    _auth(authorization, os.getenv("NODE_TOKEN"))


def _verify_evidence(mid: str, row: sqlite3.Row, node: str,
                     outcome: str, evidence: dict) -> str:
    payload = evidence.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(400, "evidence.payload must be object")
    if (payload.get("message_id") != mid or
            payload.get("node_id") != node or
            payload.get("content_sha") != row["content_sha"] or
            payload.get("channel") != row["channel"] or
            payload.get("outcome") != outcome):
        raise HTTPException(400, "evidence identity/outcome mismatch")
    canonical = json.dumps(payload, ensure_ascii=False,
                           sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(canonical).hexdigest()
    if not secrets.compare_digest(sha, str(evidence.get("sha256", ""))):
        raise HTTPException(400, "evidence sha256 mismatch")
    if outcome == "PASS":
        if row["channel"] == "code":
            checks = payload.get("checks")
            if not isinstance(checks, dict) or not (
                checks.get("content_sha256_match") is True
                and checks.get("syntax_valid") is True
                and checks.get("safe_path") is True
                and payload.get("on_disk_sha256") == row["content_sha"]
            ):
                raise HTTPException(400, "code PASS missing verified checks")
        elif row["channel"] == "voice":
            if payload.get("intent_kind") != "system_info" or not isinstance(payload.get("result"), dict):
                raise HTTPException(400, "voice PASS missing supported execution")
    return sha


@router.post("/v1/agent/inbox/claim")
def claim_inbox(req: InboxClaim, authorization: Optional[str] = Header(None)):
    _node_auth(authorization)
    with _db() as c:
        _ensure(c)
        c.commit()
        c.execute("BEGIN IMMEDIATE")
        busy = c.execute(
            "SELECT message_id FROM agent_inbox "
            "WHERE node_id=? AND status='CLAIMED' LIMIT 1", (req.node_id,)
        ).fetchone()
        if busy:
            return {"message_id": None, "reason": "node_already_claimed",
                    "claimed_message_id": busy[0]}
        row = c.execute(
            "SELECT * FROM agent_inbox WHERE node_id=? AND status='RECEIVED' "
            "ORDER BY created_at, rowid LIMIT 1", (req.node_id,)
        ).fetchone()
        if not row:
            return {"message_id": None}
        updated = c.execute(
            "UPDATE agent_inbox SET status='CLAIMED' "
            "WHERE message_id=? AND status='RECEIVED'", (row["message_id"],)
        ).rowcount
        if updated != 1:
            raise HTTPException(409, "claim conflict")
        c.execute("INSERT INTO agent_inbox_claims (message_id,node_id) VALUES (?,?)",
                  (row["message_id"], req.node_id))
        return {
            "message_id": row["message_id"], "channel": row["channel"],
            "node_id": row["node_id"], "content": row["content"],
            "content_sha": row["content_sha"], "target_file": row["target_file"],
            "description": row["description"],
            "execution_status": "CLAIMED_NOT_EXECUTED"
        }


@router.post("/v1/agent/inbox/{message_id}/result")
def finish_inbox(message_id: str, req: InboxResult,
                 authorization: Optional[str] = Header(None)):
    _node_auth(authorization)
    with _db() as c:
        _ensure(c)
        c.commit()
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT * FROM agent_inbox WHERE message_id=? AND node_id=?",
                        (message_id, req.node_id)).fetchone()
        if not row:
            raise HTTPException(404, "message not found")
        if row["status"] != "CLAIMED":
            raise HTTPException(409, "message not claimed or already finalized")
        if not c.execute(
            "SELECT 1 FROM agent_inbox_claims WHERE message_id=? AND node_id=?",
            (message_id, req.node_id)
        ).fetchone():
            raise HTTPException(409, "claim provenance missing")
        digest = _verify_evidence(message_id, row, req.node_id,
                                  req.status, req.evidence)
        final = {"PASS": "COMPLETED", "FAIL": "FAILED",
                 "BLOCKED": "BLOCKED"}[req.status]
        c.execute("INSERT INTO agent_inbox_evidence "
                  "(message_id,node_id,outcome,evidence_json) VALUES (?,?,?,?)",
                  (message_id, req.node_id, req.status,
                   json.dumps(req.evidence, ensure_ascii=False)))
        c.execute("UPDATE agent_inbox SET status=? WHERE message_id=? AND status='CLAIMED'",
                  (final, message_id))
        return {"message_id": message_id, "status": final, "sha256": digest}


@router.get("/v1/agent/inbox/{message_id}/evidence")
def get_inbox_evidence(message_id: str,
                       authorization: Optional[str] = Header(None)):
    _auth(authorization, os.getenv("D2_READ_TOKEN"))
    with _db() as c:
        _ensure(c)
        row = c.execute("SELECT evidence_json FROM agent_inbox_evidence "
                        "WHERE message_id=?", (message_id,)).fetchone()
    if not row:
        raise HTTPException(404, "evidence not found")
    return json.loads(row[0])
