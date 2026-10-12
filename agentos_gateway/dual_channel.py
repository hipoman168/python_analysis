"""DAYONG dual-channel transport: receive voice and exact code without mutating jobs."""
import hashlib
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    node_id: str = "node-02"

class CodeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500000)
    target_file: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    node_id: str = "node-02"

def _auth(header: Optional[str], token: Optional[str]):
    if not token:
        raise HTTPException(503, "transport token not configured")
    if not header or not header.startswith("Bearer ") or not secrets.compare_digest(header[7:].strip(), token):
        raise HTTPException(401, "unauthorized")

@contextmanager
def _db():
    c = sqlite3.connect(os.getenv("GATEWAY_DB", "./gateway.db"), timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS agent_inbox (
      message_id TEXT PRIMARY KEY, channel TEXT NOT NULL,
      node_id TEXT NOT NULL, content TEXT NOT NULL, content_sha TEXT NOT NULL,
      target_file TEXT, description TEXT,
      status TEXT NOT NULL DEFAULT 'RECEIVED',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    try:
        with c:
            yield c
    finally:
        c.close()

def _receive(channel, node_id, content, target_file=None, description=""):
    if not content.strip():
        raise HTTPException(400, "empty content")
    mid = ("VOICE-" if channel == "voice" else "PATCH-") + uuid.uuid4().hex
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    with _db() as c:
        c.execute("""INSERT INTO agent_inbox
        (message_id,channel,node_id,content,content_sha,target_file,description)
        VALUES (?,?,?,?,?,?,?)""",
        (mid,channel,node_id,content,digest,target_file,description))
    return {"message_id":mid,"channel":channel,"content_sha":digest,
            "status":"RECEIVED","execution_status":"NOT_DISPATCHED"}

@router.post("/v1/voice/task")
def voice(req: VoiceRequest, authorization: Optional[str] = Header(None)):
    _auth(authorization, os.getenv("VOICE_TOKEN"))
    return _receive("voice",req.node_id,req.text)

@router.post("/v1/code/patch")
def patch(req: CodeRequest, authorization: Optional[str] = Header(None)):
    _auth(authorization, os.getenv("VOICE_TOKEN"))
    if req.target_file.startswith(("/", "\\")) or ".." in req.target_file.replace("\\","/").split("/"):
        raise HTTPException(400, "invalid target_file")
    return _receive("code",req.node_id,req.text,req.target_file,req.description)

@router.get("/v1/agent/inbox")
def inbox(authorization: Optional[str] = Header(None), limit: int = 20):
    _auth(authorization, os.getenv("D2_READ_TOKEN"))
    with _db() as c:
        rows=c.execute("""SELECT message_id,channel,node_id,content_sha,target_file,
        description,status,created_at FROM agent_inbox ORDER BY created_at DESC LIMIT ?""",
        (max(1,min(limit,100)),)).fetchall()
    return {"messages":[dict(row) for row in rows]}

@router.get("/v1/agent/inbox/{message_id}")
def message(message_id: str, authorization: Optional[str] = Header(None)):
    _auth(authorization, os.getenv("D2_READ_TOKEN"))
    with _db() as c:
        row=c.execute("SELECT * FROM agent_inbox WHERE message_id=?",(message_id,)).fetchone()
    if not row:
        raise HTTPException(404,"message not found")
    return dict(row)
