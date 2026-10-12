"""Isolated deterministic inbox execution contract tests (no cloud tokens)."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("GATEWAY_DB", str(Path(tmp) / "gateway.sqlite"))
        for k, v in (("VOICE_TOKEN","voice-test"), ("CODE_TOKEN","code-test"),
                     ("NODE_TOKEN","node-test"), ("D2_READ_TOKEN","read-test")):
            monkeypatch.setenv(k, v)
        # Legacy gateway initializes jobs on import, but execution routes use GATEWAY_DB at call-time.
        from agentos_gateway.gateway import app
        yield TestClient(app)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def canonical(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {"payload": payload, "sha256": hashlib.sha256(raw).hexdigest()}


def test_code_isolation_claim_evidence(api):
    body={"text":'print("你好")\n', "target_file":"sandbox/test.py"}
    assert api.post("/v1/code/patch", headers=auth("voice-test"), json=body).status_code == 401
    rec=api.post("/v1/code/patch", headers=auth("code-test"), json=body)
    assert rec.status_code == 200, rec.text
    msg=rec.json()
    assert msg["status"]=="RECEIVED"
    assert msg["execution_status"]=="NOT_DISPATCHED"
    mid=msg["message_id"]
    assert api.post("/v1/agent/inbox/claim",headers=auth("voice-test"),json={}).status_code==401
    claim=api.post("/v1/agent/inbox/claim",headers=auth("node-test"),json={})
    assert claim.status_code==200, claim.text
    job=claim.json()
    assert job["message_id"]==mid and job["content"]==body["text"]
    assert api.post("/v1/agent/inbox/claim",headers=auth("node-test"),json={}).json()["reason"]=="node_already_claimed"
    data={"message_id":mid,"node_id":"node-02","channel":"code",
          "content_sha":msg["content_sha"],"outcome":"PASS",
          "checks":{"content_sha256_match":True,"syntax_valid":True,"safe_path":True},
          "on_disk_sha256":msg["content_sha"]}
    bad=canonical(data);bad["sha256"]="0"*64
    assert api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"node_id":"node-02","status":"PASS","evidence":bad}).status_code==400
    missing=canonical({**data,"checks":{}})
    assert api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"node_id":"node-02","status":"PASS","evidence":missing}).status_code==400
    result=api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"node_id":"node-02","status":"PASS","evidence":canonical(data)})
    assert result.status_code==200, result.text
    assert result.json()["status"]=="COMPLETED"
    assert api.get(f"/v1/agent/inbox/{mid}/evidence",headers=auth("read-test")).json()["payload"]==data
    assert api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"node_id":"node-02","status":"PASS","evidence":canonical(data)}).status_code==409
    assert api.post("/v1/agent/inbox/claim",headers=auth("node-test"),json={}).json()["message_id"] is None


@pytest.mark.parametrize("target",["../x.py","C:/evil.py","C:\\evil.py","/tmp/x.py",
                                      "folder//x.py","./x.py","\\\\server\\share\\x.py"])
def test_reject_paths(api,target):
    r=api.post("/v1/code/patch",headers=auth("code-test"),json={"text":"x=1","target_file":target})
    assert r.status_code==400, (target,r.status_code,r.text)


def test_voice_blocked_with_provenance(api):
    rec=api.post("/v1/voice/task",headers=auth("voice-test"),
                 json={"text":"關機二號機"}).json()
    mid=rec["message_id"]
    job=api.post("/v1/agent/inbox/claim",headers=auth("node-test"),json={}).json()
    assert job["message_id"]==mid
    data={"message_id":mid,"node_id":"node-02","channel":"voice",
          "content_sha":job["content_sha"],"outcome":"BLOCKED",
          "intent_kind":"unsupported","reason":"unsafe command denied"}
    result=api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"status":"BLOCKED","node_id":"node-02","evidence":canonical(data)})
    assert result.status_code==200, result.text
    assert result.json()["status"]=="BLOCKED"


def test_voice_pass_requires_actually_executed_skill(api):
    rec=api.post("/v1/voice/task",headers=auth("voice-test"),
                 json={"text":"回報機器系統資訊"}).json()
    mid=rec["message_id"]
    job=api.post("/v1/agent/inbox/claim",headers=auth("node-test"),json={}).json()
    base={"message_id":mid,"node_id":"node-02","channel":"voice",
          "content_sha":job["content_sha"],"outcome":"PASS","intent_kind":"unsupported"}
    assert api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"status":"PASS","node_id":"node-02","evidence":canonical(base)}).status_code==400
    good={**base,"intent_kind":"system_info","result":{"hostname":"test-node"}}
    assert api.post(f"/v1/agent/inbox/{mid}/result",headers=auth("node-test"),
                    json={"status":"PASS","node_id":"node-02","evidence":canonical(good)}).status_code==200
