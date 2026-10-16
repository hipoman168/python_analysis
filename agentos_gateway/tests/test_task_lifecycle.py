"""Isolated lifecycle regression. No network, GitHub account, or production DB."""
from __future__ import annotations
import hashlib
import hmac
import importlib
import json
from fastapi.testclient import TestClient

def _sig(node, tid, nonce, token, skill="system_info"):
    payload={"task_id":tid,"node_id":node,"skill_name":skill,"nonce":nonce,
             "result":{"hostname":"TEST_ONLY"}}
    from agentos_gateway.lifecycle import canonical
    raw=canonical(payload)
    return {"payload":payload,
            "sha256":hashlib.sha256(raw).hexdigest(),
            "hmac_sha256":hmac.new(token.encode(),raw,hashlib.sha256).hexdigest()}

def _client(tmp_path,monkeypatch):
    monkeypatch.setenv("GATEWAY_DB",str(tmp_path/"test_gateway.db"))
    monkeypatch.setenv("ADMIN_TOKEN","admin-test-token")
    monkeypatch.setenv("NODE_TOKEN","node2-test-token")
    monkeypatch.setenv("NODE01_TOKEN","node1-test-token")
    monkeypatch.delenv("AGENTOS_GITHUB_WAKE_TOKEN",raising=False)
    from agentos_gateway import gateway
    importlib.reload(gateway)
    return TestClient(gateway.app),gateway

def test_auto_lifecycle_two_nodes_and_audit(tmp_path,monkeypatch):
    cl,gw=_client(tmp_path,monkeypatch)
    admin={"Authorization":"Bearer admin-test-token"}
    for node,token in [("node-01","node1-test-token"),("node-02","node2-test-token")]:
        tid="T-"+node
        monkeypatch.setattr(gw.lifecycle,"dispatch_github",lambda **kw:"WAKE_ACCEPTED")
        create=cl.post("/v1/jobs",headers=admin,json={
            "task_id":tid,"node_id":node,"skill":"system_info","auto_wake":True})
        assert create.status_code==200 and create.json()["dispatch_status"]=="WAKE_ACCEPTED",create.text
        illegal={"Authorization":"Bearer "+("node2-test-token" if node=="node-01" else "node1-test-token")}
        assert cl.post(f"/v1/nodes/{node}/claim",headers=illegal,json={
            "task_id":tid,"skill":"system_info"}).status_code==403
        valid={"Authorization":"Bearer "+token}
        claim=cl.post(f"/v1/nodes/{node}/claim",headers=valid,json={"task_id":tid,"skill":"system_info"})
        assert claim.status_code==200 and claim.json()["task_id"]==tid
        nonce=claim.json()["nonce"]
        assert nonce and len(nonce)==32
        wrong=_sig(node,tid,"mismatched-nonce",token)
        assert cl.post(f"/v1/nodes/{node}/result",headers=valid,json={
            "task_id":tid,"status":"PASS","evidence":wrong}).status_code==403
        valid_ev=_sig(node,tid,nonce,token)
        done=cl.post(f"/v1/nodes/{node}/result",headers=valid,json={
            "task_id":tid,"status":"PASS","evidence":valid_ev})
        assert done.status_code==200,done.text
        assert done.json()["status"]=="COMPLETED"
        assert cl.get(f"/v1/jobs/{tid}",headers=admin).json()["status"]=="COMPLETED"
        assert cl.get(f"/v1/jobs/{tid}/evidence",headers=admin).json()["hmac_sha256"]==valid_ev["hmac_sha256"]
        audit=cl.get(f"/v1/jobs/{tid}/audit",headers=admin).json()["events"]
        assert [r["to"] for r in audit if r["to"]!="PENDING"]==["CLAIMED","COMPLETED"]
        assert cl.post(f"/v1/nodes/{node}/result",headers=valid,json={
            "task_id":tid,"status":"PASS","evidence":valid_ev}).status_code==409

def test_missing_wake_not_marked_success_and_rewake(tmp_path,monkeypatch):
    cl,gw=_client(tmp_path,monkeypatch)
    admin={"Authorization":"Bearer admin-test-token"}
    x=cl.post("/v1/jobs",headers=admin,json={
        "task_id":"T-NOWAKE","node_id":"node-01","skill":"system_info","auto_wake":True})
    assert x.status_code==200 and x.json()["dispatch_status"]=="WAKE_TOKEN_MISSING"
    assert cl.get("/v1/jobs/T-NOWAKE",headers=admin).json()["status"]=="PENDING"
    monkeypatch.setattr(gw.lifecycle,"dispatch_github",lambda **kw:"WAKE_ACCEPTED")
    x=cl.post("/v1/jobs/T-NOWAKE/wake",headers=admin)
    assert x.status_code==200 and x.json()["dispatch_status"]=="WAKE_ACCEPTED"
    y=cl.post("/v1/jobs/T-NOWAKE/wake")
    assert y.status_code==401
    assert cl.post("/v1/jobs",headers=admin,json={
        "task_id":"T-DANGEROUS","node_id":"node-01","skill":"agentos_development",
        "auto_wake":True}).status_code in (403,422)

def test_failed_result_and_stale_deadletter(tmp_path,monkeypatch):
    cl,gw=_client(tmp_path,monkeypatch)
    admin={"Authorization":"Bearer admin-test-token"}
    node={"Authorization":"Bearer node1-test-token"}
    monkeypatch.setattr(gw.lifecycle,"dispatch_github",lambda **kw:"WAKE_ACCEPTED")
    assert cl.post("/v1/jobs",headers=admin,json={
        "task_id":"T-DEAD","node_id":"node-01","skill":"system_info","auto_wake":True}).status_code==200
    for expected_attempt in (1,2,3):
        claimed=cl.post("/v1/nodes/node-01/claim",headers=node,
                        json={"skill":"system_info","task_id":"T-DEAD"}).json()
        assert claimed["task_id"]=="T-DEAD"
        with gw.sqlite3.connect(gw.DB) as c:
            assert c.execute("SELECT attempts FROM jobs WHERE task_id='T-DEAD'").fetchone()[0]==expected_attempt
            c.execute("UPDATE jobs SET claimed_at=? WHERE task_id='T-DEAD'",
                      ("2000-01-01T00:00:00+00:00",))
    nojob=cl.post("/v1/nodes/node-01/claim",headers=node,
                  json={"skill":"system_info","task_id":"T-DEAD"})
    assert nojob.status_code==200 and nojob.json()["task_id"] is None
    assert cl.get("/v1/jobs/T-DEAD",headers=admin).json()["status"]=="DEADLETTER"
    assert any(x["to"]=="DEADLETTER" for x in
               cl.get("/v1/jobs/T-DEAD/audit",headers=admin).json()["events"])

def test_legacy_backcompat(tmp_path,monkeypatch):
    cl,gw=_client(tmp_path,monkeypatch)
    adm={"Authorization":"Bearer admin-test-token"}
    tok={"Authorization":"Bearer node2-test-token"}
    assert cl.post("/v1/jobs",headers=adm,json={
        "task_id":"T-LEGACY","node_id":"node-02","skill":"system_info"}).status_code==200
    claim=cl.post("/v1/nodes/node-02/claim",headers=tok).json()
    assert claim["task_id"]=="T-LEGACY"
    payload={"task_id":"T-LEGACY","node_id":"node-02","skill_name":"system_info"}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,
                                    separators=(",",":")).encode()).hexdigest()
    result=cl.post("/v1/nodes/node-02/result",headers=tok,
                   json={"task_id":"T-LEGACY","status":"PASS",
                         "evidence":{"payload":payload,"sha256":digest}})
    assert result.status_code==200,result.text
    assert result.json()["status"]=="COMPLETED"

def test_wrong_skill_and_target_not_stealable(tmp_path,monkeypatch):
    cl,gw=_client(tmp_path,monkeypatch)
    adm={"Authorization":"Bearer admin-test-token"}
    node={"Authorization":"Bearer node2-test-token"}
    for tid,skill in [("T-DEV","agentos_development"),("T-INFO","system_info")]:
        assert cl.post("/v1/jobs",headers=adm,json={
            "task_id":tid,"node_id":"node-02","skill":skill}).status_code==200
    c=cl.post("/v1/nodes/node-02/claim",headers=node,
              json={"skill":"system_info","task_id":"T-INFO"}).json()
    assert c["task_id"]=="T-INFO"
    assert cl.get("/v1/jobs/T-DEV",headers=adm).json()["status"]=="PENDING"


def test_retry_rotates_nonce_and_old_result_rejected(tmp_path, monkeypatch):
    cl, gw = _client(tmp_path, monkeypatch)
    admin = {"Authorization": "Bearer admin-test-token"}
    node = {"Authorization": "Bearer node1-test-token"}
    monkeypatch.setattr(gw.lifecycle, "dispatch_github", lambda **kw: "WAKE_ACCEPTED")
    assert cl.post("/v1/jobs",headers=admin,json={
        "task_id":"T-ROTATE-RETRY","node_id":"node-01",
        "skill":"system_info","auto_wake":True}).status_code==200
    first=cl.post("/v1/nodes/node-01/claim",headers=node,
                  json={"task_id":"T-ROTATE-RETRY","skill":"system_info"}).json()
    old_nonce=first["nonce"]
    with gw.sqlite3.connect(gw.DB) as db:
        db.execute("UPDATE jobs SET claimed_at=? WHERE task_id='T-ROTATE-RETRY'",
                   ("2000-01-01T00:00:00+00:00",))
    stale=_sig("node-01","T-ROTATE-RETRY",old_nonce,"node1-test-token")
    assert cl.post("/v1/nodes/node-01/result",headers=node,json={
        "task_id":"T-ROTATE-RETRY","status":"PASS",
        "evidence":stale}).status_code==409
    second=cl.post("/v1/nodes/node-01/claim",headers=node,
                   json={"task_id":"T-ROTATE-RETRY","skill":"system_info"}).json()
    assert second["task_id"]=="T-ROTATE-RETRY" and second["nonce"]!=old_nonce
    assert cl.post("/v1/nodes/node-01/result",headers=node,json={
        "task_id":"T-ROTATE-RETRY","status":"PASS",
        "evidence":stale}).status_code==403
    fresh=_sig("node-01","T-ROTATE-RETRY",second["nonce"],"node1-test-token")
    assert cl.post("/v1/nodes/node-01/result",headers=node,json={
        "task_id":"T-ROTATE-RETRY","status":"PASS","evidence":fresh
    }).json()["status"]=="COMPLETED"
