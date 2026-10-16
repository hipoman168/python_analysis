"""DAYONG AgentOS Node-01 one-shot outbound worker (stdlib, no pip deps).

Uses only HTTPS Render broker, only system_info, no shell commands,
no arbitrary file writes, no high-frequency polling.
The bearer token must be supplied by the machine's protected local launcher.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import platform
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

NODE_ID = "node-01"
GATEWAY = "https://dayong-agentos-gateway.onrender.com"
EVIDENCE_DIR = Path(r"C:\DAYONG_AI\agentos\evidence\node01_bridge")

def _canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")

def _post(path, token, body):
    if not path.startswith("/v1/") or ".." in path:
        raise ValueError("DENIED_PATH")
    req = urllib.request.Request(
        GATEWAY + path, data=_canonical(body),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "User-Agent": "DAYONG-AgentOS-Node01-Worker/1"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise RuntimeError("RESPONSE_TOO_LARGE")
            return json.loads(data)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GATEWAY_HTTP_" + str(exc.code)) from None

def run_once():
    token = os.getenv("NODE_TOKEN")
    if not token or len(token) < 24:
        raise RuntimeError("NODE_TOKEN_NOT_PROVISIONED")
    claim = _post("/v1/nodes/" + NODE_ID + "/claim", token, {})
    tid = claim.get("task_id")
    if not tid:
        return {"node_id": NODE_ID, "status": "NO_PENDING_JOB",
                "reason": claim.get("reason")}
    if not isinstance(tid, str) or len(tid) > 128 or "/" in tid or "\\" in tid:
        raise ValueError("INVALID_TASK_ID")
    # The server permits only system_info for Node-01 bootstrap.
    skill = claim.get("skill")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if skill == "system_info":
        outcome = "PASS"
        result = {"hostname": socket.gethostname(),
                  "system": platform.system(),
                  "release": platform.release(),
                  "python_version": platform.python_version(),
                  "cpu_count": os.cpu_count()}
        reason = None
    else:
        outcome = "FAIL"
        result = None
        reason = "SKILL_NOT_ALLOWED_NODE01"
    payload = {"node_id": NODE_ID, "task_id": tid,
               "skill_name": skill, "agent_id": "node01-worker",
               "result": result, "reason_code": reason,
               "generated_at": now}
    raw = _canonical(payload)
    ev = {"payload": payload, "sha256": hashlib.sha256(raw).hexdigest(),
          "size_bytes": len(raw)}
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    dest = EVIDENCE_DIR / (tid + ".json")
    with dest.open("x", encoding="utf-8") as f:
        json.dump(ev, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    response = _post("/v1/nodes/" + NODE_ID + "/result", token,
                     {"task_id": tid, "status": outcome, "evidence": ev})
    return {"node_id": NODE_ID, "task_id": tid,
            "status": response.get("status"), "sha256": ev["sha256"]}

if __name__ == "__main__":
    print(json.dumps(run_once(), ensure_ascii=False))
