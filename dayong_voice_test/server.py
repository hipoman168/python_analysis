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


def fetch_json(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: int = 90) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(raw)


def bridge_headers(content: bool = False) -> dict:
    h = {"x-dayong-bridge-token": BRIDGE_TOKEN}
    if content:
        h["Content-Type"] = "application/json"
    return h


def family_post(sender_id: str, sender_name: str, content: str, session_id: str, recipient_id: str | None = None, message_type: str = "CHAT", metadata: dict | None = None) -> dict:
    if not BRIDGE_TOKEN:
        return {"ok": False, "error": "bridge_token_not_configured"}
    try:
        _, out = fetch_json(FAMILY_BUS + "/message", method="POST", body={
            "sender_id": sender_id, "sender_name": sender_name, "recipient_id": recipient_id,
            "message_type": message_type, "content": content, "session_id": session_id,
            "source": "RENDER_FAMILY_VOICE", "metadata": metadata or {}
        }, headers=bridge_headers(True), timeout=20)
        return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def inworld_submit_and_wait(text: str, agent: str, mode: str, session_id: str) -> dict:
    if not BRIDGE_TOKEN:
        raise RuntimeError("bridge_token_not_configured")
    _, submitted = fetch_json(INWORLD_QUEUE + "/submit", method="POST",
        body={"text": text, "agent": agent, "mode": mode, "session_id": session_id},
        headers=bridge_headers(True), timeout=30)
    job_id = submitted.get("job_id")
    if not job_id:
        raise RuntimeError("inworld_job_not_created")
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        _, state = fetch_json(INWORLD_QUEUE + "/job?id=" + urllib.parse.quote(str(job_id)), headers=bridge_headers(), timeout=20)
        job = state.get("job") or {}
        status = job.get("status")
        if status == "COMPLETED":
            result = job.get("result") or {}
            result["job_id"] = str(job_id)
            return result
        if status == "FAILED":
            raise RuntimeError("inworld_worker_failed: " + str(job.get("error") or "unknown"))
        time.sleep(0.08)
    raise TimeoutError("inworld_job_timeout")


def startup_probe():
    try:
        if UPSTREAM:
            _, h = fetch_json(UPSTREAM + "/health")
            print("UPSTREAM_HEALTH " + json.dumps(h, ensure_ascii=False), flush=True)
        _, fh = fetch_json(FAMILY_BUS + "/health", headers=bridge_headers(), timeout=20)
        print("FAMILY_ROOM_HEALTH " + json.dumps(fh, ensure_ascii=False), flush=True)
    except Exception as exc:
        print("STARTUP_PROBE_ERROR " + repr(exc), flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "DAYONG-Voice-Gateway/0.6"

    def log_message(self, fmt, *args):
        print("VOICE_HTTP", self.address_string(), fmt % args, flush=True)

    def send_json(self, status: int, obj: dict):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 20000:
            raise ValueError("invalid_body_size")
        return json.loads(self.rfile.read(length).decode())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            raw = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if parsed.path == "/api/family/health":
            try:
                _, j = fetch_json(FAMILY_BUS + "/health", headers=bridge_headers(), timeout=20)
                self.send_json(200, j)
            except Exception as exc:
                self.send_json(502, {"ok": False, "error": "family_bus_unavailable", "detail": str(exc)[:240]})
            return
        if parsed.path == "/api/family/messages":
            try:
                qs = urllib.parse.parse_qs(parsed.query)
                limit = str(min(100, max(1, int((qs.get("limit") or ["40"])[0]))))
                _, j = fetch_json(FAMILY_BUS + "/messages?limit=" + limit, headers=bridge_headers(), timeout=20)
                self.send_json(200, j)
            except Exception as exc:
                self.send_json(502, {"ok": False, "error": "family_messages_unavailable", "detail": str(exc)[:240]})
            return
        if parsed.path == "/api/health":
            queue_ok = False
            family_ok = False
            try:
                _, q = fetch_json(INWORLD_QUEUE + "/health", timeout=15)
                queue_ok = bool(q.get("ok"))
            except Exception:
                pass
            try:
                _, f = fetch_json(FAMILY_BUS + "/health", headers=bridge_headers(), timeout=15)
                family_ok = bool(f.get("ok"))
            except Exception:
                pass
            if not UPSTREAM:
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.6", "room_id": ROOM_ID, "family_bus": family_ok, "inworld_queue": queue_ok, "agents": {"CEO-002": False, "D1": False, "D2": False}})
                return
            try:
                _, j = fetch_json(UPSTREAM + "/health")
                agents = j.get("agents", {})
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.6", "room_id": ROOM_ID, "family_bus": family_ok, "inworld_queue": queue_ok, "low_latency_poll_ms": 80, "voices": {"D1": "Sarah", "D2": "Dennis"}, "agents": {"CEO-002": bool(agents.get("CEO-002")), "D1": bool(agents.get("D1")), "D2": bool(agents.get("D2"))}, "upstream": j})
            except Exception as exc:
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.6", "room_id": ROOM_ID, "family_bus": family_ok, "inworld_queue": queue_ok, "agents": {"CEO-002": False, "D1": False, "D2": False}, "upstream_error": str(exc)[:240]})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        try:
            obj = self.read_body()
            if self.path == "/api/family/message":
                text = str(obj.get("text", "")).strip()
                if not text or len(text) > 4000:
                    raise ValueError("invalid_text")
                sid = str(obj.get("session_id") or uuid.uuid4())
                out = family_post(str(obj.get("sender_id") or "CHAIRMAN-001"), str(obj.get("sender_name") or "何董事長"), text, sid, obj.get("recipient_id"), str(obj.get("message_type") or "CHAT"), obj.get("metadata") or {})
                self.send_json(200 if out.get("ok") else 502, out)
                return

            text = str(obj.get("text", "")).strip()
            if not text or len(text) > 4000:
                raise ValueError("invalid_text")
            sid = str(obj.get("session_id") or uuid.uuid4())

            if self.path == "/api/inworld":
                agent = "D2" if str(obj.get("agent", "D1")).upper() == "D2" else "D1"
                mode = "realtime" if str(obj.get("mode", "standard")).lower() == "realtime" else "standard"
                result = inworld_submit_and_wait(text[:800], agent, mode, sid)
                self.send_json(200, {"session_id": sid, "agent": agent, "mode": mode, "result": result})
                return

            if self.path != "/api/conference":
                self.send_json(404, {"error": "not_found"})
                return
            if not UPSTREAM or not BRIDGE_TOKEN:
                self.send_json(503, {"error": "upstream_not_configured"})
                return

            human_receipt = family_post("CHAIRMAN-001", "何董事長", text, sid, metadata={"kind": "voice_turn"})
            _, upstream = fetch_json(UPSTREAM + "/conference", method="POST", body={"text": text, "session_id": sid, "room_id": ROOM_ID}, headers=bridge_headers(True))
            turns = upstream.get("turns", [])
            receipts = []
            for t in turns:
                reply = str(t.get("reply") or "").strip()
                if not reply:
                    continue
                aid = "D2-004" if str(t.get("agent")).upper() == "D2" else "D1-003"
                receipts.append(family_post(aid, str(t.get("agent_name") or aid), reply, sid, metadata={"model": t.get("model"), "status": t.get("status"), "kind": "agent_voice_turn"}))
            self.send_json(200, {"session_id": sid, "room_id": ROOM_ID, "mode": upstream.get("mode", "NATURAL_NAME_ROUTING"), "targets": upstream.get("targets", []), "turns": turns, "family_bus": {"human": human_receipt, "agents": receipts}})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            self.send_json(502, {"error": "upstream_http_error", "http_status": exc.code, "detail": detail})
        except Exception as exc:
            self.send_json(400 if isinstance(exc, ValueError) else 500, {"error": type(exc).__name__, "detail": str(exc)[:500]})


if __name__ == "__main__":
    print(json.dumps({"event": "VOICE_GATEWAY_START", "version": "0.6", "room_id": ROOM_ID, "host": HOST, "port": PORT, "upstream_configured": bool(UPSTREAM and BRIDGE_TOKEN), "family_bus": FAMILY_BUS, "inworld_queue": INWORLD_QUEUE}, ensure_ascii=False), flush=True)
    startup_probe()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
