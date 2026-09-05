from __future__ import annotations
import os
os.environ.setdefault("DAYONG_VOICE_HOST", "0.0.0.0")
os.environ.setdefault("DAYONG_VOICE_PORT", os.getenv("PORT", "10000"))
import server

def _do_head(self):
    self.send_response(200)
    self.send_header("Content-Type", "text/plain; charset=utf-8")
    self.send_header("Content-Length", "0")
    self.send_header("Cache-Control", "no-store")
    self.end_headers()

server.Handler.do_HEAD = _do_head

if __name__ == "__main__":
    print("DAYONG_RENDER_VOICE_START", flush=True)
    server.startup_probe()
    server.ThreadingHTTPServer((server.HOST, server.PORT), server.Handler).serve_forever()
