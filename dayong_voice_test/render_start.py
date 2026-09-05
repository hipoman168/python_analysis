from __future__ import annotations
import json
import os
import urllib.error

os.environ.setdefault("DAYONG_VOICE_HOST", "0.0.0.0")
os.environ.setdefault("DAYONG_VOICE_PORT", os.getenv("PORT", "10000"))
import server

AUDITION_URL = os.getenv("DAYONG_VOICE_AUDITION_URL", "https://slsxzbevdoctwnncywwh.supabase.co/functions/v1/voice-audition").rstrip("/")

def _do_head(self):
    self.send_response(200); self.send_header("Content-Type","text/plain; charset=utf-8"); self.send_header("Content-Length","0"); self.send_header("Cache-Control","no-store"); self.end_headers()

_original_get=server.Handler.do_GET
_original_post=server.Handler.do_POST

def _serve_audition_page(self):
    raw=(server.ROOT/"audition.html").read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(raw)

def _audition_get(self):
    path=self.path.split("?",1)[0]
    if path in {"/audition","/audition/","/audition.html"}: return _serve_audition_page(self)
    if path!="/api/voice-audition/health": return _original_get(self)
    try:
        status,out=server.fetch_json(AUDITION_URL,headers=server.bridge_headers(),timeout=20); self.send_json(status,out)
    except urllib.error.HTTPError as exc:
        self.send_json(502,{"ok":False,"error":"fixed_voice_http_error","http_status":exc.code,"detail":exc.read().decode("utf-8",errors="replace")[:500]})
    except Exception as exc: self.send_json(502,{"ok":False,"error":"fixed_voice_unavailable","detail":str(exc)[:500]})

def _fixed_voice_post(self):
    path=self.path.split("?",1)[0]
    if path not in {"/api/voice-audition","/api/fixed-voice"}: return _original_post(self)
    try:
        obj=self.read_body(); role=str(obj.get("role") or "").upper(); text=str(obj.get("text") or "").strip()
        if role not in {"CEO-002","D1","D2"}: raise ValueError("invalid_role")
        payload={"role":role}
        if text: payload["text"]=text[:800]
        status,out=server.fetch_json(AUDITION_URL,method="POST",body=payload,headers=server.bridge_headers(True),timeout=45); self.send_json(status,out)
    except urllib.error.HTTPError as exc:
        self.send_json(502,{"ok":False,"error":"fixed_voice_http_error","http_status":exc.code,"detail":exc.read().decode("utf-8",errors="replace")[:500]})
    except Exception as exc: self.send_json(400 if isinstance(exc,ValueError) else 502,{"ok":False,"error":type(exc).__name__,"detail":str(exc)[:500]})

server.Handler.do_HEAD=_do_head
server.Handler.do_GET=_audition_get
server.Handler.do_POST=_fixed_voice_post

def audition_startup_probe():
    try:
        _,out=server.fetch_json(AUDITION_URL,headers=server.bridge_headers(),timeout=20); print("FIXED_VOICE_HEALTH "+json.dumps(out,ensure_ascii=False),flush=True)
    except Exception as exc: print("FIXED_VOICE_HEALTH_ERROR "+repr(exc),flush=True)

if __name__=="__main__":
    print("DAYONG_RENDER_VOICE_START",flush=True); server.startup_probe(); audition_startup_probe(); server.ThreadingHTTPServer((server.HOST,server.PORT),server.Handler).serve_forever()
