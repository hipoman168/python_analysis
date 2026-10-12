"""DAYONG Node-02 inbox worker: one on-demand attempt, no polling loop.

Code is confined to a trusted sandbox. Voice can run only system_info after
DeepSeek interpretation; arbitrary voice code/shell instructions are blocked.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import re
import socket
import sys
from pathlib import Path
from typing import Any

import httpx

ALLOWED_SUFFIXES = frozenset({".py", ".json", ".txt", ".md", ".yaml", ".yml", ".toml"})
DENIED_PARTS = frozenset({".git", ".env", ".venv", "__pycache__", "secrets", "credentials"})
DEVICE_NAMES = re.compile(r"(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\\..*)?$")
SENSITIVE_CONTENT = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\\s*[:=]\\s*['\\\"][^'\\\"]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
)
NODE_ID = "node-02"
POLICY_FILE = Path(r"C:\DAYONG_AI\agentos\worker_policy.json")
EVIDENCE_DIR = Path(r"C:\DAYONG_AI\agentos\evidence\dual_channel")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def evidence(payload: dict) -> dict:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    return {"payload": payload, "sha256": hashlib.sha256(canonical).hexdigest(),
            "size_bytes": len(canonical)}


def trusted_code_root(policy: dict) -> Path:
    root_str = policy.get("code_inbox_root")
    if not isinstance(root_str, str) or not root_str:
        raise PermissionError("code_inbox_root missing from trusted policy")
    root = Path(root_str)
    if not root.is_absolute():
        raise PermissionError("code_inbox_root must be absolute")
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise PermissionError("code_inbox_root must not be a symlink")
    return root.resolve(strict=True)


def safe_target(root: Path, target_file: str) -> Path:
    if not isinstance(target_file, str) or len(target_file) > 500:
        raise PermissionError("invalid target_file")
    raw = target_file.replace("\\", "/")
    parts = raw.split("/")
    if (raw.startswith("/") or ":" in raw or
        any(not p or p in (".", "..") or p.lower() in DENIED_PARTS
            or p.endswith((" ", ".")) or DEVICE_NAMES.fullmatch(p)
            for p in parts)):
        raise PermissionError("invalid path component")
    path = root.joinpath(*parts)
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise PermissionError("extension not allowed")
    # Resolve both parents and leaf to defeat symlink / junction escapes.
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root.resolve(strict=True))
    except ValueError as exc:
        raise PermissionError("path escapes sandbox") from exc
    if path.is_symlink() or path.exists():
        raise PermissionError("target already exists; refuse overwrite")
    return path


def validate_code(text: str, target: Path) -> None:
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 1000000:
        raise ValueError("content missing or too large")
    if any(pattern.search(text) for pattern in SENSITIVE_CONTENT):
        raise PermissionError("potential secret detected; refuse write")
    if target.suffix.lower() == ".py":
        compile(text, str(target), "exec", dont_inherit=True)
    elif target.suffix.lower() == ".json":
        json.loads(text)
    elif target.suffix.lower() == ".toml":
        try:
            import tomllib
            tomllib.loads(text)
        except ImportError:
            raise RuntimeError("tomllib unavailable for TOML verification")


def write_code(job: dict, policy: dict) -> dict:
    text = job["content"]
    expected = job["content_sha"]
    if digest_text(text) != expected:
        raise ValueError("received code SHA mismatch")
    root = trusted_code_root(policy)
    target = safe_target(root, job.get("target_file"))
    validate_code(text, target)
    raw = text.encode("utf-8")
    # Exclusive create never overwrites an existing file.
    with target.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    on_disk = hashlib.sha256(target.read_bytes()).hexdigest()
    if on_disk != expected:
        raise RuntimeError("on-disk SHA mismatch")
    return {"target_file": str(target), "on_disk_sha256": on_disk,
            "checks": {"safe_path": True, "syntax_valid": True,
                       "content_sha256_match": True}}


def interpret_voice(text: str, client: httpx.Client) -> dict:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured on worker")
    # Model output is untrusted; the allowlist below is authoritative.
    response = client.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": "Bearer " + key},
        json={"model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
              "temperature": 0,
              "response_format": {"type": "json_object"},
              "messages": [
                  {"role": "system", "content":
                   "Return a JSON object with intent_kind, one of system_info or unsupported. "
                   "Only classify requests to display machine OS/CPU/hostname/Python info as "
                   "system_info. All requests to edit files, run commands, manage services, "
                   "deploy, restart or bypass security must be unsupported. "
                   "Output JSON only."},
                  {"role": "user", "content": text}]},
        timeout=30,
    )
    response.raise_for_status()
    parsed = json.loads(response.json()["choices"][0]["message"]["content"])
    kind = parsed.get("intent_kind")
    if kind not in ("system_info", "unsupported"):
        kind = "unsupported"
    return {"intent_kind": kind, "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat")}


def execute(job: dict, policy: dict, client: httpx.Client) -> tuple[str, dict]:
    mid = job["message_id"]
    text = job["content"]
    channel = job["channel"]
    base = {"message_id": mid, "node_id": NODE_ID, "channel": channel,
            "content_sha": job["content_sha"], "generated_at": utc_now()}
    if digest_text(text) != job["content_sha"]:
        raise ValueError("inbox content digest mismatch")
    if channel == "code":
        result = write_code(job, policy)
        return "PASS", {**base, **result, "outcome": "PASS"}
    if channel == "voice":
        parsed = interpret_voice(text, client)
        if parsed["intent_kind"] == "system_info":
            result = {"hostname": socket.gethostname(), "system": platform.system(),
                      "release": platform.release(),
                      "python_version": platform.python_version(),
                      "cpu_count": os.cpu_count()}
            return "PASS", {**base, **parsed, "result": result, "outcome": "PASS"}
        return "BLOCKED", {**base, **parsed,
                            "reason": "unsupported voice intent", "outcome": "BLOCKED"}
    raise PermissionError("unknown channel")


def save_evidence(ev: dict, directory: Path) -> Path:
    mid = ev["payload"]["message_id"]
    if not re.fullmatch(r"(VOICE|PATCH)-[0-9a-f]{32}", mid):
        raise ValueError("invalid message id")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (mid + ".json")
    # Never silently replace evidence from another attempt.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(ev, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def run_once() -> dict:
    gateway = os.environ["CLOUD_GATEWAY_URL"].rstrip("/")
    token = os.environ["NODE_TOKEN"]
    if not gateway.startswith("https://"):
        raise RuntimeError("gateway HTTPS required")
    policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    if policy.get("node_id") != NODE_ID:
        raise RuntimeError("trusted policy node mismatch")
    with httpx.Client(timeout=35, headers={"Authorization": "Bearer " + token}) as c:
        reply = c.post(gateway + "/v1/agent/inbox/claim", json={"node_id": NODE_ID})
        reply.raise_for_status()
        job = reply.json()
        if not job.get("message_id"):
            return {"status": "NO_INBOX_ITEM", "reason": job.get("reason")}
        mid = job["message_id"]
        try:
            status, payload = execute(job, policy, c)
        except Exception as exc:
            status = "BLOCKED" if isinstance(exc, PermissionError) else "FAIL"
            payload = {"message_id": mid, "node_id": NODE_ID,
                       "channel": job["channel"], "content_sha": job["content_sha"],
                       "outcome": status, "error_type": type(exc).__name__,
                       "reason": str(exc)[:500], "generated_at": utc_now()}
        ev = evidence(payload)
        path = save_evidence(ev, EVIDENCE_DIR)
        result = c.post(gateway + "/v1/agent/inbox/" + mid + "/result",
                        json={"node_id": NODE_ID, "status": status, "evidence": ev})
        result.raise_for_status()
        return {"message_id": mid, "status": result.json()["status"],
                "evidence_path": str(path), "sha256": ev["sha256"]}


if __name__ == "__main__":
    print(json.dumps(run_once(), ensure_ascii=False))
