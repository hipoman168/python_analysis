"""Pure staging tests: no real credentials, hosts, or user node calls."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys

from fastapi.testclient import TestClient

def _evidence(task_id, node_id):
    payload={"task_id":task_id, "node_id":node_id, "skill_name":"system_info",
             "result":{"hostname":"TEST_NODE"}}
    sha=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,
                   separators=(",",":")).encode("utf-8")).hexdigest()
    return {"payload":payload,"sha256":sha}

def test_dual_node_auth_and_evidence(tmp_path,monkeypatch):
    monkeypatch.setenv("GATEWAY_DB",str(tmp_path/"gateway.db"))
    monkeypatch.setenv("ADMIN_TOKEN","test-admin-do-not-use")
    monkeypatch.setenv("NODE_TOKEN","test-node02-do-not-use")
    monkeypatch.delenv("NODE01_TOKEN",raising=False)
    import agentos_gateway.gateway as gw
    importlib.reload(gw)
    client=TestClient(gw.app)
    admin={"authorization":"Bearer test-admin-do-not-use"}
    node02={"authorization":"Bearer test-node02-do-not-use"}
    # Node-01 cannot receive jobs before unique credential enrollment.
    unready=client.post("/v1/jobs",headers=admin,
                        json={"task_id":"T-1","node_id":"node-01","skill":"system_info"})
    assert unready.status_code == 503
    monkeypatch.setenv("NODE01_TOKEN","test-node01-do-not-use")
    node01={"authorization":"Bearer test-node01-do-not-use"}
    assert client.post("/v1/jobs",headers=admin,json={
        "task_id":"T-X","node_id":"node-01","skill":"agentos_development"}).status_code==403
    assert client.post("/v1/jobs",headers=admin,json={
        "task_id":"T-Y","node_id":"unknown","skill":"system_info"}).status_code==403
    create=client.post("/v1/jobs",headers=admin,json={
        "task_id":"T-1","node_id":"node-01","skill":"system_info"})
    assert create.status_code==200,create.text
    # Different machines never share bearer identity.
    assert client.post("/v1/nodes/node-01/claim",headers=node02).status_code==403
    assert client.post("/v1/nodes/node-02/claim",headers=node01).status_code==403
    claim=client.post("/v1/nodes/node-01/claim",headers=node01)
    assert claim.status_code==200 and claim.json()["task_id"]=="T-1"
    result=client.post("/v1/nodes/node-01/result",headers=node01,json={
        "task_id":"T-1","status":"PASS","evidence":_evidence("T-1","node-01")})
    assert result.status_code==200 and result.json()["status"]=="COMPLETED"
    assert client.get("/v1/jobs/T-1",headers=admin).json()["status"]=="COMPLETED"
    assert client.get("/v1/jobs/T-1/evidence",headers=admin).json()["sha256"]==result.json()["sha256"]
    # Legacy Node-02 behaviour remains operational and independent.
    create2=client.post("/v1/jobs",headers=admin,json={
        "task_id":"T-2","node_id":"node-02","skill":"system_info"})
    assert create2.status_code==200,create2.text
    claim2=client.post("/v1/nodes/node-02/claim",headers=node02)
    assert claim2.status_code==200 and claim2.json()["task_id"]=="T-2"
    result2=client.post("/v1/nodes/node-02/result",headers=node02,json={
        "task_id":"T-2","status":"PASS","evidence":_evidence("T-2","node-02")})
    assert result2.status_code==200, result2.text
    assert client.get("/v1/jobs/T-2",headers=admin).json()["status"]=="COMPLETED"

def test_node01_worker_is_allowlisted(monkeypatch):
    from agentos_gateway import node01_outbound_worker as worker
    import pytest
    called=[]
    def fake_post(path,token,body):
        called.append(path)
        if path.endswith("/claim"):
            return {"task_id":None}
        raise AssertionError("No result call without claim")
    monkeypatch.setattr(worker,"_post",fake_post)
    monkeypatch.setenv("NODE_TOKEN","test-node01-do-not-use")
    assert worker.run_once()["status"]=="NO_PENDING_JOB"
    assert called==["/v1/nodes/node-01/claim"]
