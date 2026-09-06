#!/usr/bin/env python3
"""DAYONG modular Linux safe executor.

Transport is deliberately separate from action handlers. This process claims
governed tool requests from the existing command-seat tool gateway and only
executes named, allowlisted handlers. It never accepts arbitrary shell text.
"""
import hashlib
import json
import os
import time
import urllib.request

from voice_gateway import execute_voice_gateway_action

AGENT_ID = os.getenv("DAYONG_AGENT_ID", "CEO-002")
NODE_ID = os.getenv("DAYONG_NODE_ID", "DY-CN-SHANGHAI-001")
GATEWAY = os.getenv(
    "DAYONG_TOOL_GATEWAY_URL",
    "https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/command-seat-tool-gateway",
)
KEY = os.getenv("DAYONG_MCP_API_KEY", "")
POLL_SECONDS = max(2, int(os.getenv("DAYONG_TOOL_POLL_SECONDS", "5")))
EXECUTOR_VERSION = "DAYONG_LINUX_SAFE_EXECUTOR_V2"


def post(body):
    req = urllib.request.Request(
        GATEWAY,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"content-type": "application/json", "x-dayong-mcp-key": KEY},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=90).read().decode())


def api(action, **kwargs):
    return post({"action": action, "agent_id": AGENT_ID, **kwargs})


def execute(request):
    tool = str(request.get("tool_name", "")).upper()
    action = str(request.get("action_name", "")).upper()
    args = request.get("arguments") or {}
    if tool != "LOCAL_LINUX_SAFE":
        raise ValueError("TOOL_NOT_IMPLEMENTED_BY_LINUX_EXECUTOR")
    return execute_voice_gateway_action(action, args)


def once():
    q = api("claim_tool_execution", node_id=NODE_ID)
    if not q.get("claimed"):
        return False
    request_id = q["request_id"]
    api("start_tool_execution", request_id=request_id)
    evidence = {
        "agent_id": AGENT_ID,
        "node_id": NODE_ID,
        "executor": EXECUTOR_VERSION,
        "tool_name": q.get("tool_name"),
        "action_name": q.get("action_name"),
    }
    try:
        ok, detail = execute(q)
        evidence["detail"] = detail
        digest = hashlib.sha256(
            json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        api(
            "complete_tool_execution",
            request_id=request_id,
            ok=bool(ok),
            result_ref=f"inline://sha256/{digest}",
            evidence=evidence,
            error=None if ok else "HANDLER_RETURNED_NONZERO",
        )
    except Exception as exc:
        evidence["error_type"] = type(exc).__name__
        api(
            "complete_tool_execution",
            request_id=request_id,
            ok=False,
            result_ref=None,
            evidence=evidence,
            error=str(exc)[:1000],
        )
    return True


def main():
    if not KEY:
        raise RuntimeError("DAYONG_MCP_API_KEY is required")
    while True:
        try:
            once()
        except Exception as exc:
            print(f"linux-safe-executor error: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
