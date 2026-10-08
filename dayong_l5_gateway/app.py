import os, json, sqlite3, uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="DAYONG L5 Message Gateway", version="0.1.0")
DB = os.getenv("L5_DB_PATH", "/tmp/l5-messages.db")
TOKEN = os.getenv("L5_GATEWAY_TOKEN")
def auth(authorization):
    if not TOKEN or authorization != "Bearer " + TOKEN:
        raise HTTPException(401, "unauthorized")
def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, sender TEXT NOT NULL, recipient TEXT NOT NULL, task_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, ack_at TEXT, reply TEXT, replied_at TEXT, evidence TEXT)")
    c.commit()
    return c
class Message(BaseModel):
    sender: str
    recipient: str
    task_id: str
    payload: dict
    evidence: Optional[dict]=None
class Reply(BaseModel):
    sender: str
    payload: dict
    evidence: Optional[dict]=None
@app.get("/health")
def health(): return {"service":"DAYONG-L5","status":"UP","persistence":"DEMO_ONLY_SQLITE_EPHEMERAL"}
@app.post("/v1/messages")
def send(m:Message, authorization:Optional[str]=Header(None)):
    auth(authorization)
    mid=str(uuid.uuid4()); now=datetime.now(timezone.utc).isoformat()
    with conn() as c:
        c.execute("INSERT INTO messages(id,sender,recipient,task_id,payload,status,created_at,evidence) VALUES(?,?,?,?,?,?,?,?)",(mid,m.sender,m.recipient,m.task_id,json.dumps(m.payload),"SENT",now,json.dumps(m.evidence)))
    return {"id":mid,"status":"SENT"}
@app.get("/v1/messages")
def inbox(recipient:str, authorization:Optional[str]=Header(None)):
    auth(authorization)
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM messages WHERE recipient=? ORDER BY created_at DESC LIMIT 100",(recipient,))]
@app.post("/v1/messages/{message_id}/ack")
def ack(message_id:str, recipient:str, authorization:Optional[str]=Header(None)):
    auth(authorization)
    with conn() as c:
        r=c.execute("SELECT recipient,status FROM messages WHERE id=?",(message_id,)).fetchone()
        if not r: raise HTTPException(404)
        if r["recipient"]!=recipient: raise HTTPException(403)
        if r["status"]!="SENT": raise HTTPException(409)
        c.execute("UPDATE messages SET status='ACKED',ack_at=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),message_id))
    return {"id":message_id,"status":"ACKED"}
@app.post("/v1/messages/{message_id}/reply")
def reply(message_id:str, body:Reply, authorization:Optional[str]=Header(None)):
    auth(authorization)
    with conn() as c:
        r=c.execute("SELECT recipient,status FROM messages WHERE id=?",(message_id,)).fetchone()
        if not r: raise HTTPException(404)
        if r["recipient"]!=body.sender: raise HTTPException(403)
        if r["status"]!="ACKED": raise HTTPException(409,"ACK required")
        c.execute("UPDATE messages SET status='REPLIED',reply=?,replied_at=?,evidence=? WHERE id=?",(json.dumps(body.payload),datetime.now(timezone.utc).isoformat(),json.dumps(body.evidence),message_id))
    return {"id":message_id,"status":"REPLIED"}
