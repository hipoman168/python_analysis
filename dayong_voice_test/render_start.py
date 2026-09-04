from __future__ import annotations
import os
os.environ.setdefault("DAYONG_VOICE_HOST", "0.0.0.0")
os.environ.setdefault("DAYONG_VOICE_PORT", os.getenv("PORT", "10000"))
import server
if __name__ == "__main__":
    print("DAYONG_RENDER_VOICE_START", flush=True)
    server.ThreadingHTTPServer((server.HOST, server.PORT), server.Handler).serve_forever()
