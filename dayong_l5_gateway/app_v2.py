import os, json, uuid, hmac, hashlib
from datetime import datetime, timezone
from contextlib import contextmanager
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import psycopg
from psycopg.rows import dict_row

app = FastAPI(title="DAYONG L5 Gateway", version="0.2.0")
DATABASE_URL = os.getenv("L5_DATABASE_URL", "")
AGENT_KEYS_JSON = os.getenv("L5_AGENT_KEYS_JSON", "{}")

def identity(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    try:
        keys = json.loads(AGENT_KEYS_JSON)
        for agent_id, key in keys.items():
            if key and hmac.compare_digest(authorization[7:], key):
                return agent_id
    except (ValueError, TypeError):
        pass
    raise HTTPException(401, "Invalid agent credential")

@contextmanager
def db():
    if not DATABASE_URL:
        raise HTTPException(503, "Persistent database not configured")
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn

class Message(BaseModel):
    recipient_agent_id: str
    task_id: str
    task_version: int = Field(default=1, ge=1)
    payload: dict
    correlation_id: Optional[uuid.UUID] = None
    required_skills: list[str] = Field(default_factory=list)
    evidence: dict = Field(default_factory=dict)

class Receipt(BaseModel):
    evidence: dict = Field(default_factory=dict)
    reason: Optional[str] = None

class Reply(BaseModel):
    payload: dict
    evidence: dict = Field(default_factory=dict)

def log(c, mid, actor, kind, payload):
    c.execute("INSERT INTO l5_events(message_id,actor_agent_id,event_type,event_payload) VALUES (%s,%s,%s,%s::jsonb)",(mid,actor,kind,json.dumps(payload)))

@app.get("/health")
def health():
    return {"service":"DAYONG-L5","version":"0.2.0","configured":bool(DATABASE_URL and AGENT_KEYS_JSON != "{}")}

@app.post("/v1/messages")
def send(m:Message, authorization:Optional[str]=Header(None)):
    sender=identity(authorization)
    mid=uuid.uuid4()
    with db() as c:
        agents=c.execute("SELECT agent_id FROM l5_agents WHERE agent_id IN (%s,%s) AND active=true",(sender,m.recipient_agent_id)).fetchall()
        if len(agents)!=2 or sender==m.recipient_agent_id: raise HTTPException(403,"Inactive or unknown sender/recipient")
        c.execute("""INSERT INTO l5_messages(message_id,correlation_id,task_id,task_version,sender_agent_id,recipient_agent_id,payload,required_skills,evidence)
          VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)""",(mid,m.correlation_id or uuid.uuid4(),m.task_id,m.task_version,sender,m.recipient_agent_id,json.dumps(m.payload),json.dumps(m.required_skills),json.dumps(m.evidence)))
        log(c,mid,sender,"SENT",{})
    return {"message_id":str(mid),"status":"SENT"}

@app.get("/v1/messages")
def inbox(authorization:Optional[str]=Header(None)):
    actor=identity(authorization)
    with db() as c:
        return c.execute("SELECT * FROM l5_messages WHERE recipient_agent_id=%s ORDER BY created_at DESC LIMIT 100",(actor,)).fetchall()

def transition(mid, actor, old, new, evidence, reason=None, reply=None):
    with db() as c:
        row=c.execute("SELECT recipient_agent_id,status FROM l5_messages WHERE message_id=%s FOR UPDATE",(mid,)).fetchone()
        if not row: raise HTTPException(404,"Message not found")
        if row["recipient_agent_id"]!=actor: raise HTTPException(403,"Not recipient")
        if row["status"]!=old: raise HTTPException(409,"Invalid state transition")
        c.execute("UPDATE l5_messages SET status=%s,ack_at=CASE WHEN %s LIKE 'ACK_%%' THEN now() ELSE ack_at END,replied_at=CASE WHEN %s='REPLIED' THEN now() ELSE replied_at END,reply_payload=COALESCE(%s::jsonb,reply_payload),evidence=evidence || %s::jsonb WHERE message_id=%s",(new,new,new,json.dumps(reply) if reply is not None else None,json.dumps(evidence),mid))
        log(c,mid,actor,new,{"reason":reason,"evidence":evidence})
    return {"message_id":str(mid),"status":new}

@app.post("/v1/messages/{message_id}/ack")
def ack(message_id:uuid.UUID, body:Receipt, accepted:bool=True, authorization:Optional[str]=Header(None)):
    actor=identity(authorization)
    return transition(message_id,actor,"SENT","ACK_ACCEPTED" if accepted else "ACK_REJECTED",body.evidence,body.reason)

@app.post("/v1/messages/{message_id}/reply")
def reply(message_id:uuid.UUID, body:Reply, authorization:Optional[str]=Header(None)):
    return transition(message_id,identity(authorization),"ACK_ACCEPTED","REPLIED",body.evidence,reply=body.payload)

@app.post("/v1/messages/{message_id}/confirm")
def confirm(message_id:uuid.UUID, authorization:Optional[str]=Header(None)):
    actor=identity(authorization)
    with db() as c:
        row=c.execute("SELECT sender_agent_id,status FROM l5_messages WHERE message_id=%s FOR UPDATE",(message_id,)).fetchone()
        if not row: raise HTTPException(404)
        if row["sender_agent_id"]!=actor: raise HTTPException(403)
        if row["status"]!="REPLIED": raise HTTPException(409)
        c.execute("UPDATE l5_messages SET status='DELIVERY_CONFIRMED',confirmed_at=now() WHERE message_id=%s",(message_id,))
        log(c,message_id,actor,"DELIVERY_CONFIRMED",{})
    return {"message_id":str(message_id),"status":"DELIVERY_CONFIRMED"}
