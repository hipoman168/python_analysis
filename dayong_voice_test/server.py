from __future__ import annotations

import json, os, pathlib, urllib.request, urllib.error, urllib.parse, uuid, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
HOST = os.getenv("DAYONG_VOICE_HOST", "0.0.0.0")
PORT = int(os.getenv("DAYONG_VOICE_PORT", os.getenv("PORT", "10000")))
UPSTREAM = os.getenv("DAYONG_SUPABASE_VOICE_URL", "").rstrip("/")
BRIDGE_TOKEN = os.getenv("DAYONG_BRIDGE_TOKEN", "")
INWORLD_QUEUE = os.getenv("DAYONG_INWORLD_QUEUE_URL", "https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/inworld-voice-queue").rstrip("/")
FAMILY_BUS = os.getenv("DAYONG_FAMILY_BUS_URL", "https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/family-room-bus").rstrip("/")
ROOM_ID = "DAYONG-FAMILY-ROOM"


def fetch_json(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: int = 90):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(raw)


def bridge_headers(content: bool = False):
    h = {"x-dayong-bridge-token": BRIDGE_TOKEN}
    if content: h["Content-Type"] = "application/json"
    return h


def family_post(sender_id, sender_name, content, session_id, recipient_id=None, message_type="CHAT", metadata=None):
    if not BRIDGE_TOKEN: return {"ok": False, "error": "bridge_token_not_configured"}
    try:
        _, out = fetch_json(FAMILY_BUS + "/message", method="POST", body={
            "sender_id": sender_id, "sender_name": sender_name, "recipient_id": recipient_id,
            "message_type": message_type, "content": content, "session_id": session_id,
            "source": "RENDER_FAMILY_VOICE", "metadata": metadata or {}
        }, headers=bridge_headers(True), timeout=20)
        return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def inworld_submit_and_wait(text, agent, mode, session_id):
    if not BRIDGE_TOKEN: raise RuntimeError("bridge_token_not_configured")
    _, submitted = fetch_json(INWORLD_QUEUE + "/submit", method="POST", body={"text": text, "agent": agent, "mode": mode, "session_id": session_id}, headers=bridge_headers(True), timeout=30)
    job_id = submitted.get("job_id")
    if not job_id: raise RuntimeError("inworld_job_not_created")
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        _, state = fetch_json(INWORLD_QUEUE + "/job?id=" + urllib.parse.quote(str(job_id)), headers=bridge_headers(), timeout=20)
        job = state.get("job") or {}; status = job.get("status")
        if status == "COMPLETED":
            result = job.get("result") or {}; result["job_id"] = str(job_id); return result
        if status == "FAILED": raise RuntimeError("inworld_worker_failed: " + str(job.get("error") or "unknown"))
        time.sleep(0.08)
    raise TimeoutError("inworld_job_timeout")


def recent_history(limit=20):
    try:
        _, j = fetch_json(FAMILY_BUS + f"/messages?limit={limit}", headers=bridge_headers(), timeout=20)
        rows = j.get("messages") or []
        return "\n".join(f"{m.get('sender_name') or m.get('sender_id')}: {m.get('content','')}" for m in rows[-limit:])
    except Exception:
        return ""


def startup_probe():
    try:
        if UPSTREAM:
            _, h = fetch_json(UPSTREAM + "/health"); print("UPSTREAM_HEALTH " + json.dumps(h, ensure_ascii=False), flush=True)
        _, fh = fetch_json(FAMILY_BUS + "/health", headers=bridge_headers(), timeout=20); print("FAMILY_ROOM_HEALTH " + json.dumps(fh, ensure_ascii=False), flush=True)
    except Exception as exc:
        print("STARTUP_PROBE_ERROR " + repr(exc), flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "DAYONG-Voice-Gateway/0.7"
    def log_message(self, fmt, *args): print("VOICE_HTTP", self.address_string(), fmt % args, flush=True)
    def send_json(self, status, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode(); self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(raw)
    def read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 20000: raise ValueError("invalid_body_size")
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            raw = (ROOT / "index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(raw))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(raw); return
        if parsed.path == "/api/family/messages":
            try:
                qs = urllib.parse.parse_qs(parsed.query); limit = str(min(100, max(1, int((qs.get("limit") or ["40"])[0])))); _, j = fetch_json(FAMILY_BUS + "/messages?limit=" + limit, headers=bridge_headers(), timeout=20); self.send_json(200, j)
            except Exception as exc: self.send_json(502, {"ok": False, "error": "family_messages_unavailable", "detail": str(exc)[:240]})
            return
        if parsed.path == "/api/health":
            family_ok = queue_ok = False
            try: _, q = fetch_json(INWORLD_QUEUE + "/health", timeout=15); queue_ok = bool(q.get("ok"))
            except Exception: pass
            try: _, f = fetch_json(FAMILY_BUS + "/health", headers=bridge_headers(), timeout=15); family_ok = bool(f.get("ok"))
            except Exception: pass
            try:
                _, j = fetch_json(UPSTREAM + "/health") if UPSTREAM else (200, {"agents": {}}); agents = j.get("agents", {})
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.7", "room_id": ROOM_ID, "family_bus": family_ok, "inworld_queue": queue_ok, "discussion_mode": bool(j.get("discussion_mode")), "ceo_provider_role_fallback": bool(j.get("ceo_provider_role_fallback")), "agents": {"CEO-002": bool(agents.get("CEO-002")), "D1": bool(agents.get("D1")), "D2": bool(agents.get("D2"))}, "upstream": j})
            except Exception as exc: self.send_json(200, {"ok": True, "version": "0.7", "family_bus": family_ok, "inworld_queue": queue_ok, "agents": {"CEO-002": False, "D1": False, "D2": False}, "upstream_error": str(exc)[:240]})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        try:
            obj = self.read_body(); text = str(obj.get("text", "")).strip(); sid = str(obj.get("session_id") or uuid.uuid4())
            if not text or len(text) > 4000: raise ValueError("invalid_text")
            if self.path == "/api/family/message":
                out = family_post(str(obj.get("sender_id") or "CHAIRMAN-001"), str(obj.get("sender_name") or "何董事長"), text, sid, obj.get("recipient_id"), str(obj.get("message_type") or "CHAT"), obj.get("metadata") or {}); self.send_json(200 if out.get("ok") else 502, out); return
            if self.path == "/api/inworld":
                agent = "D2" if str(obj.get("agent", "D1")).upper() == "D2" else "D1"; mode = "realtime" if str(obj.get("mode", "standard")).lower() == "realtime" else "standard"; result = inworld_submit_and_wait(text[:800], agent, mode, sid); self.send_json(200, {"session_id": sid, "agent": agent, "mode": mode, "result": result}); return
            if not UPSTREAM or not BRIDGE_TOKEN: self.send_json(503, {"error": "upstream_not_configured"}); return
            if self.path == "/api/discussion":
                family_post("CHAIRMAN-001", "何董事長", text, sid, message_type="TOPIC", metadata={"kind": "family_discussion_topic"})
                _, upstream = fetch_json(UPSTREAM + "/discussion", method="POST", body={"text": text, "session_id": sid, "room_id": ROOM_ID, "history": recent_history(20)}, headers=bridge_headers(True), timeout=120)
                turns = upstream.get("turns", []); receipts=[]
                for t in turns:
                    reply = str(t.get("reply") or "").strip()
                    if not reply: continue
                    raw_id = str(t.get("agent") or ""); aid = "CEO-002" if raw_id == "CEO-002" else ("D2-004" if raw_id == "D2" else "D1-003")
                    receipts.append(family_post(aid, str(t.get("agent_name") or aid), reply, sid, message_type="DISCUSSION_TURN", metadata={"model": t.get("model"), "voice": t.get("voice"), "provider_role_fallback": t.get("provider_role_fallback", False)}))
                self.send_json(200, {"ok": True, "session_id": sid, "room_id": ROOM_ID, "mode": "FAMILY_DISCUSSION", "turns": turns, "family_bus_receipts": receipts}); return
            if self.path == "/api/conference":
                family_post("CHAIRMAN-001", "何董事長", text, sid, metadata={"kind": "voice_turn"})
                _, upstream = fetch_json(UPSTREAM + "/conference", method="POST", body={"text": text, "session_id": sid, "room_id": ROOM_ID}, headers=bridge_headers(True)); turns = upstream.get("turns", []); receipts=[]
                for t in turns:
                    reply = str(t.get("reply") or "").strip()
                    if not reply: continue
                    raw_id = str(t.get("agent") or ""); aid = "CEO-002" if raw_id == "CEO-002" else ("D2-004" if raw_id == "D2" else "D1-003")
                    receipts.append(family_post(aid, str(t.get("agent_name") or aid), reply, sid, metadata={"model": t.get("model"), "kind": "agent_voice_turn"}))
                self.send_json(200, {"session_id": sid, "room_id": ROOM_ID, "mode": upstream.get("mode", "FAMILY_NAME_ROUTING"), "targets": upstream.get("targets", []), "turns": turns, "family_bus": receipts}); return
            self.send_json(404, {"error": "not_found"})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]; self.send_json(502, {"error": "upstream_http_error", "http_status": exc.code, "detail": detail})
        except Exception as exc:
            self.send_json(400 if isinstance(exc, ValueError) else 500, {"error": type(exc).__name__, "detail": str(exc)[:500]})

if __name__ == "__main__":
    print(json.dumps({"event": "VOICE_GATEWAY_START", "version": "0.7", "room_id": ROOM_ID, "host": HOST, "port": PORT, "discussion_mode": True}, ensure_ascii=False), flush=True); startup_probe(); ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
