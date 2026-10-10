import os, sqlite3, json, secrets, hashlib
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB = os.getenv('GATEWAY_DB','./gateway.db')
NODE_TOKEN = os.getenv('NODE_TOKEN','')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN','')
D2_READ_TOKEN = os.getenv('D2_READ_TOKEN','')
app = FastAPI(title='DAYONG AgentOS Outbound Gateway', version='0.0.8')

def init():
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS jobs (task_id TEXT PRIMARY KEY, node_id TEXT NOT NULL, skill TEXT NOT NULL, status TEXT NOT NULL, evidence TEXT, created_at TEXT NOT NULL)')
init()

class Job(BaseModel):
    task_id: str = Field(min_length=1)
    node_id: str = 'node-02'
    skill: str = 'system_info'

class Result(BaseModel):
    task_id: str
    status: str
    evidence: dict

def read_auth(authorization):
    if not authorization or not any(t and secrets.compare_digest(authorization, 'Bearer '+t) for t in (ADMIN_TOKEN,D2_READ_TOKEN)):
        raise HTTPException(401, 'Unauthorized')

def auth(authorization, token):
    if not token or not authorization or not secrets.compare_digest(authorization, 'Bearer '+token):
        raise HTTPException(401, 'Unauthorized')

@app.get('/health')
def health(): return {'status':'ok','version':'0.0.8'}

@app.post('/v1/jobs')
def create_job(job:Job, authorization:str|None=Header(None)):
    auth(authorization,ADMIN_TOKEN)
    if job.skill!='system_info': raise HTTPException(403,'Skill not allowed')
    with sqlite3.connect(DB) as c:
        c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)',(job.task_id,job.node_id,job.skill,'PENDING',None,datetime.now(timezone.utc).isoformat()))
    return {'task_id':job.task_id,'status':'PENDING'}

@app.post('/v1/nodes/{node_id}/claim')
def claim(node_id:str, authorization:str|None=Header(None)):
    auth(authorization,NODE_TOKEN)
    with sqlite3.connect(DB) as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT task_id,skill FROM jobs WHERE node_id=? AND status='PENDING' ORDER BY created_at LIMIT 1",(node_id,)).fetchone()
        if row: c.execute("UPDATE jobs SET status='CLAIMED' WHERE task_id=? AND status='PENDING'",(row[0],))
    return {'task_id':row[0],'skill':row[1]} if row else {'task_id':None}

@app.post('/v1/nodes/{node_id}/result')
def submit_result(node_id:str, result:Result, authorization:str|None=Header(None)):
    auth(authorization,NODE_TOKEN)
    e=result.evidence
    payload=e.get('payload')
    if not isinstance(payload,dict) or payload.get('task_id')!=result.task_id or payload.get('node_id')!=node_id:
        raise HTTPException(400,'Evidence identity mismatch')
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    if not secrets.compare_digest(digest,str(e.get('sha256',''))): raise HTTPException(400,'Evidence hash mismatch')
    with sqlite3.connect(DB) as c:
        cursor=c.execute("UPDATE jobs SET status=?,evidence=? WHERE task_id=? AND node_id=? AND status='CLAIMED'",('COMPLETED' if result.status=='PASS' else 'FAILED',json.dumps(e,ensure_ascii=False),result.task_id,node_id))
        if not cursor.rowcount: raise HTTPException(409,'Task not claimed')
    return {'task_id':result.task_id,'status':'COMPLETED' if result.status=='PASS' else 'FAILED','sha256':digest}

@app.get('/v1/jobs/{task_id}')
def get_job(task_id:str, authorization:str|None=Header(None)):
    read_auth(authorization)
    with sqlite3.connect(DB) as c: row=c.execute('SELECT task_id,node_id,skill,status,evidence FROM jobs WHERE task_id=?',(task_id,)).fetchone()
    if not row: raise HTTPException(404,'Not found')
    return dict(zip(['task_id','node_id','skill','status','evidence'],[row[0],row[1],row[2],row[3],json.loads(row[4]) if row[4] else None]))

@app.get('/v1/jobs/{task_id}/evidence')
def get_evidence(task_id:str, authorization:str|None=Header(None)):
    read_auth(authorization)
    with sqlite3.connect(DB) as c:
        row=c.execute('SELECT evidence FROM jobs WHERE task_id=?',(task_id,)).fetchone()
    if not row: raise HTTPException(404,'Task not found')
    if not row[0]: raise HTTPException(404,'Evidence not yet available')
    return json.loads(row[0])
