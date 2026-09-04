from __future__ import annotations

import json, os, pathlib, urllib.request, urllib.error, urllib.parse, uuid, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
HOST = os.getenv("DAYONG_VOICE_HOST", "0.0.0.0")
PORT = int(os.getenv("DAYONG_VOICE_PORT", os.getenv("PORT", "10000")))
UPSTREAM = os.getenv("DAYONG_SUPABASE_VOICE_URL", "").rstrip("/")
BRIDGE_TOKEN = os.getenv("DAYONG_BRIDGE_TOKEN", "")
INWORLD_QUEUE = os.getenv(
    "DAYONG_INWORLD_QUEUE_URL",
    "https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/inworld-voice-queue",
).rstrip("/")


def fetch_json(url: str, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: int = 90) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return resp.status, json.loads(raw)


def queue_headers() -> dict:
    return {"Content-Type": "application/json", "x-dayong-bridge-token": BRIDGE_TOKEN}


def inworld_submit_and_wait(text: str, agent: str, mode: str, session_id: str) -> dict:
    if not BRIDGE_TOKEN:
        raise RuntimeError("bridge_token_not_configured")
    _, submitted = fetch_json(
        INWORLD_QUEUE + "/submit",
        method="POST",
        body={"text": text, "agent": agent, "mode": mode, "session_id": session_id},
        headers=queue_headers(),
        timeout=30,
    )
    job_id = submitted.get("job_id")
    if not job_id:
        raise RuntimeError("inworld_job_not_created")

    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        _, state = fetch_json(
            INWORLD_QUEUE + "/job?id=" + urllib.parse.quote(str(job_id)),
            headers={"x-dayong-bridge-token": BRIDGE_TOKEN},
            timeout=20,
        )
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
    if not UPSTREAM:
        print("UPSTREAM_HEALTH UNCONFIGURED", flush=True)
        return
    try:
        _, h = fetch_json(UPSTREAM + "/health")
        print("UPSTREAM_HEALTH " + json.dumps(h, ensure_ascii=False), flush=True)
        agents = h.get("agents", {})
        if BRIDGE_TOKEN and agents.get("D1") and agents.get("D2"):
            _, s = fetch_json(
                UPSTREAM + "/conference",
                method="POST",
                body={"text": "請各用一句話回覆：語音橋接測試成功。"},
                headers={"Content-Type": "application/json", "x-dayong-bridge-token": BRIDGE_TOKEN},
            )
            brief = [{"agent": t.get("agent"), "status": t.get("status"), "model": t.get("model"), "reply": (t.get("reply") or "")[:80]} for t in s.get("turns", [])]
            print("UPSTREAM_SMOKE " + json.dumps(brief, ensure_ascii=False), flush=True)
        else:
            print("UPSTREAM_SMOKE SKIPPED_AGENTS_NOT_READY", flush=True)
        try:
            _, q = fetch_json(INWORLD_QUEUE + "/health", timeout=20)
            print("INWORLD_QUEUE_HEALTH " + json.dumps(q, ensure_ascii=False), flush=True)
        except Exception as qexc:
            print("INWORLD_QUEUE_PROBE_ERROR " + repr(qexc), flush=True)
    except Exception as exc:
        print("UPSTREAM_PROBE_ERROR " + repr(exc), flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "DAYONG-Voice-Gateway/0.5"

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

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            raw = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == "/api/health":
            queue_ok = False
            try:
                _, q = fetch_json(INWORLD_QUEUE + "/health", timeout=15)
                queue_ok = bool(q.get("ok"))
            except Exception:
                pass
            if not UPSTREAM:
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.5", "conference": True, "inworld_queue": queue_ok, "agents": {"CEO-002": False, "D1": False, "D2": False}, "upstream": "UNCONFIGURED"})
                return
            try:
                _, j = fetch_json(UPSTREAM + "/health")
                agents = j.get("agents", {})
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.5", "conference": True, "inworld_queue": queue_ok, "low_latency_poll_ms": 80, "voices": {"D1": "Sarah", "D2": "Dennis"}, "agents": {"CEO-002": False, "D1": bool(agents.get("D1")), "D2": bool(agents.get("D2"))}, "upstream": j})
            except Exception as exc:
                self.send_json(200, {"ok": True, "service": "dayong-voice-gateway", "version": "0.5", "conference": True, "inworld_queue": queue_ok, "agents": {"CEO-002": False, "D1": False, "D2": False}, "upstream_error": str(exc)[:240]})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 20000:
                raise ValueError("invalid_body_size")
            obj = json.loads(self.rfile.read(length).decode())
            text = str(obj.get("text", "")).strip()
            if not text or len(text) > 4000:
                raise ValueError("invalid_text")

            if self.path == "/api/inworld":
                agent = "D2" if str(obj.get("agent", "D1")).upper() == "D2" else "D1"
                mode = "realtime" if str(obj.get("mode", "standard")).lower() == "realtime" else "standard"
                sid = str(obj.get("session_id") or uuid.uuid4())
                result = inworld_submit_and_wait(text[:800], agent, mode, sid)
                self.send_json(200, {"session_id": sid, "agent": agent, "mode": mode, "result": result})
                return

            if self.path != "/api/conference":
                self.send_json(404, {"error": "not_found"})
                return
            if not UPSTREAM or not BRIDGE_TOKEN:
                self.send_json(503, {"error": "upstream_not_configured"})
                return
            sid = str(obj.get("session_id") or uuid.uuid4())
            _, upstream = fetch_json(
                UPSTREAM + "/conference",
                method="POST",
                body={"text": text, "session_id": sid},
                headers={"Content-Type": "application/json", "x-dayong-bridge-token": BRIDGE_TOKEN},
            )
            self.send_json(200, {"session_id": sid, "mode": upstream.get("mode", "NATURAL_NAME_ROUTING"), "targets": upstream.get("targets", []), "turns": upstream.get("turns", [])})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            self.send_json(502, {"error": "upstream_http_error", "http_status": exc.code, "detail": detail})
        except Exception as exc:
            self.send_json(400 if isinstance(exc, ValueError) else 500, {"error": type(exc).__name__, "detail": str(exc)[:500]})


if __name__ == "__main__":
    print(json.dumps({"event": "VOICE_GATEWAY_START", "version": "0.5", "host": HOST, "port": PORT, "upstream_configured": bool(UPSTREAM and BRIDGE_TOKEN), "inworld_queue": INWORLD_QUEUE, "queue_poll_ms": 80}, ensure_ascii=False), flush=True)
    startup_probe()
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
