from __future__ import annotations

import json, os, pathlib, time, urllib.error, urllib.request, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
HOST = os.getenv("DAYONG_VOICE_HOST", "127.0.0.1")
PORT = int(os.getenv("DAYONG_VOICE_PORT", "8765"))
DEFAULT_MODEL = os.getenv("DAYONG_DEEPSEEK_MODEL", "deepseek-chat")

AGENTS = {
    "CEO-002": {
        "name": "002 陳啟航／CEO",
        "key": os.getenv("DAYONG_CEO_API_KEY", ""),
        "base": os.getenv("DAYONG_CEO_BASE_URL", "").rstrip("/"),
        "model": os.getenv("DAYONG_CEO_MODEL", ""),
        "system": "你是大用科技工號002陳啟航，總控AI／CEO。會議中先做總控判斷，口語精簡、繁體中文，不假裝擁有未提供的工具權限。",
    },
    "D1": {
        "name": "D1 小晴",
        "key": os.getenv("DAYONG_D1_API_KEY", ""),
        "base": (os.getenv("DAYONG_D1_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com").rstrip("/"),
        "model": DEFAULT_MODEL,
        "system": "你是大用科技 D1 小晴。會議中補充不同觀點，不重複前一位；自然、精簡、適合口語播報的繁體中文。",
    },
    "D2": {
        "name": "D2 阿凱",
        "key": os.getenv("DAYONG_D2_API_KEY", ""),
        "base": (os.getenv("DAYONG_D2_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com").rstrip("/"),
        "model": DEFAULT_MODEL,
        "system": "你是大用科技 D2 阿凱。會議中做風險檢查或第二意見，不重複前面內容；自然、精簡、適合口語播報的繁體中文。",
    },
}
SESSIONS: dict[str, list[dict]] = {}
MAX_HISTORY = 12

def configured(cfg: dict) -> bool:
    return bool(cfg.get("key") and cfg.get("base") and cfg.get("model"))

def call_agent(agent_id: str, text: str, context: list[dict] | None = None) -> dict:
    cfg = AGENTS[agent_id]
    if not configured(cfg):
        raise RuntimeError(f"credential_unavailable:{agent_id}")
    messages = [{"role": "system", "content": cfg["system"]}]
    for item in (context or [])[-6:]:
        messages.append({"role": "user", "content": f"會議紀錄：{item['speaker']}：{item['text']}"})
    messages.append({"role": "user", "content": text})
    payload = {"model": cfg["model"], "messages": messages, "temperature": 0.35, "stream": False}
    req = urllib.request.Request(cfg["base"] + "/chat/completions", data=json.dumps(payload, ensure_ascii=False).encode(), method="POST", headers={"Authorization": "Bearer " + cfg["key"], "Content-Type": "application/json", "Accept": "application/json"})
    started = time.time()
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read().decode("utf-8", errors="replace"))
        reply = body["choices"][0]["message"]["content"].strip()
        return {"agent": agent_id, "agent_name": cfg["name"], "reply": reply, "http_status": resp.status, "latency_ms": round((time.time()-started)*1000), "model": body.get("model")}

def conference(text: str, session_id: str) -> dict:
    history = SESSIONS.setdefault(session_id, [])
    history.append({"speaker": "何董事長", "text": text})
    turns = []
    for agent_id in ("CEO-002", "D1", "D2"):
        cfg = AGENTS[agent_id]
        if not configured(cfg):
            turns.append({"agent": agent_id, "agent_name": cfg["name"], "status": "UNAVAILABLE", "reply": None})
            continue
        prompt = text
        prior = [f"{t['agent_name']}：{t['reply']}" for t in turns if t.get("reply")]
        if prior:
            prompt += "\n前面與會者已說：\n" + "\n".join(prior) + "\n請只補充新的重點。"
        result = call_agent(agent_id, prompt, history)
        result["status"] = "OK"
        turns.append(result)
        history.append({"speaker": result["agent_name"], "text": result["reply"]})
    SESSIONS[session_id] = history[-MAX_HISTORY:]
    return {"session_id": session_id, "mode": "THREE_SEAT_SEQUENTIAL", "turn_order": ["CEO-002", "D1", "D2"], "turns": turns}

class Handler(BaseHTTPRequestHandler):
    server_version = "DAYONG-Voice-Gateway/0.2"
    def log_message(self, fmt, *args): print("VOICE_HTTP", self.address_string(), fmt % args, flush=True)
    def send_json(self, status, obj):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path in ("/","/index.html"):
            raw=(ROOT/"index.html").read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(raw); return
        if self.path=="/api/health":
            self.send_json(200,{"ok":True,"service":"dayong-voice-gateway","version":"0.2","conference":True,"agents":{k:configured(v) for k,v in AGENTS.items()}}); return
        self.send_json(404,{"error":"not_found"})
    def do_POST(self):
        try:
            length=int(self.headers.get("Content-Length","0"))
            if length<=0 or length>20000: raise ValueError("invalid_body_size")
            obj=json.loads(self.rfile.read(length).decode()); text=str(obj.get("text","")).strip()
            if not text or len(text)>4000: raise ValueError("invalid_text")
            if self.path=="/api/conference":
                sid=str(obj.get("session_id") or uuid.uuid4()); self.send_json(200,conference(text,sid)); return
            if self.path=="/api/voice-router":
                agent=str(obj.get("agent","")).strip()
                if agent not in AGENTS: raise ValueError("unsupported_agent")
                if not configured(AGENTS[agent]): self.send_json(503,{"agent":agent,"error":"agent_not_configured"}); return
                self.send_json(200,call_agent(agent,text)); return
            self.send_json(404,{"error":"not_found"})
        except urllib.error.HTTPError as exc: self.send_json(502,{"error":"provider_http_error","http_status":exc.code})
        except Exception as exc: self.send_json(400 if isinstance(exc,ValueError) else 500,{"error":type(exc).__name__,"detail":str(exc)[:300]})

if __name__=="__main__":
    print(json.dumps({"event":"VOICE_GATEWAY_START","version":"0.2","host":HOST,"port":PORT,"agents":{k:configured(v) for k,v in AGENTS.items()}},ensure_ascii=False),flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
