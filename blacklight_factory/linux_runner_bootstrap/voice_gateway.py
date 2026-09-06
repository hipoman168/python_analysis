#!/usr/bin/env python3
"""Replaceable voice-gateway handler for DAYONG Linux Safe Executor.

Each action is fixed and idempotent. No caller-supplied shell/argv is accepted.
"""
import json
import pathlib
import subprocess
import urllib.request

SERVICE = "dayong-voice"
ENV_FILE = pathlib.Path("/opt/dayong-voice/dayong-voice.env")
DROPIN_DIR = pathlib.Path("/etc/systemd/system/dayong-voice.service.d")
RUNTIME_DROPIN = DROPIN_DIR / "runtime-env.conf"
PYTHON = "/opt/dayong-cabinet/venv/bin/python"
SERVER = "/opt/dayong-voice/server.py"
HEALTH_URL = "https://139.196.108.23/voice-test/api/health"
INWORLD_URL = "https://139.196.108.23/voice-test/api/inworld"


def run(argv, timeout=60):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, shell=False)
    return p.returncode == 0, {
        "argv": argv,
        "returncode": p.returncode,
        "stdout": (p.stdout or "")[-8000:],
        "stderr": (p.stderr or "")[-8000:],
    }


def env_token_present_in_file():
    if not ENV_FILE.is_file():
        return False
    for line in ENV_FILE.read_text(errors="replace").splitlines():
        if line.startswith("DAYONG_BRIDGE_TOKEN=") and len(line.split("=", 1)[1]) > 0:
            return True
    return False


def repair_env():
    if not env_token_present_in_file():
        return False, {"reason": "BRIDGE_TOKEN_NOT_PRESENT_IN_ENV_FILE"}
    DROPIN_DIR.mkdir(parents=True, exist_ok=True)
    content = (
        "[Service]\n"
        "ExecStart=\n"
        f"ExecStart=/bin/bash -lc 'set -a; . {ENV_FILE}; set +a; exec {PYTHON} {SERVER}'\n"
    )
    if not RUNTIME_DROPIN.exists() or RUNTIME_DROPIN.read_text() != content:
        RUNTIME_DROPIN.write_text(content)
    ok1, e1 = run(["systemctl", "daemon-reload"])
    ok2, e2 = run(["systemctl", "restart", SERVICE]) if ok1 else (False, {})
    ok3, e3 = run(["systemctl", "is-active", SERVICE]) if ok2 else (False, {})
    return ok1 and ok2 and ok3 and e3.get("stdout", "").strip() == "active", {
        "daemon_reload": e1,
        "restart": e2,
        "active": e3,
        "token_file_present": True,
        "secret_redacted": True,
    }


def status():
    ok, detail = run(["systemctl", "is-active", SERVICE])
    return ok and detail.get("stdout", "").strip() == "active", detail


def logs():
    ok, detail = run(["journalctl", "-u", SERVICE, "-n", "80", "--no-pager"], 60)
    for key in ("stdout", "stderr"):
        s = detail.get(key, "")
        for marker in ("DAYONG_BRIDGE_TOKEN=", "x-dayong-bridge-token"):
            if marker in s:
                s = s.replace(marker, "[REDACTED_MARKER]=")
        detail[key] = s
    return ok, detail


def http_json(url, method="GET", body=None, timeout=60):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json", "user-agent": "DAYONG-Linux-Safe-Executor/2"},
        method=method,
    )
    import ssl
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.status, json.loads(r.read().decode())


def acceptance(mode):
    health_status, health = http_json(HEALTH_URL)
    if health_status != 200 or not health.get("ok") or not health.get("inworld_queue"):
        return False, {"health": health, "stage": "HEALTH"}
    body = {
        "text": f"你好，這是大用科技上海伺服器 {mode.capitalize()} 語音自動驗收測試。",
        "agent": "D1",
        "mode": mode,
        "session_id": f"linux-runner-{mode}-acceptance",
    }
    try:
        status_code, result = http_json(INWORLD_URL, "POST", body, 60)
    except Exception as exc:
        return False, {"health": health, "stage": mode.upper(), "error": str(exc)[:1000]}
    passed = status_code == 200 and bool(result)
    return passed, {"health": health, "stage": mode.upper(), "response": result, "http_status": status_code}


def execute_voice_gateway_action(action, args):
    del args
    if action == "VOICE_GATEWAY_ENV_REPAIR":
        return repair_env()
    if action == "VOICE_GATEWAY_RESTART":
        ok, detail = run(["systemctl", "restart", SERVICE])
        if not ok:
            return False, detail
        return status()
    if action == "VOICE_GATEWAY_STATUS":
        return status()
    if action == "VOICE_GATEWAY_LOG_READ":
        return logs()
    if action == "VOICE_GATEWAY_STANDARD_ACCEPTANCE":
        return acceptance("standard")
    if action == "VOICE_GATEWAY_REALTIME_ACCEPTANCE":
        return acceptance("realtime")
    raise ValueError("LINUX_ACTION_NOT_ALLOWLISTED")
