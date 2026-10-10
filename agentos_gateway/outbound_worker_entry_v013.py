"""DAYONG outbound Worker single-run entrypoint for Windows Task Scheduler.
No inbound port, remote desktop, or high-frequency polling required.
Schedule only when there is an explicit task window; otherwise manual/API-triggered worker.
"""
from pathlib import Path
import json
import os
import sys
from datetime import datetime, timezone

from node_worker_v007 import main

def run():
    log_dir = Path(os.environ.get("AGENTOS_LOG_DIR", r"C:\DAYONG_AI\agentos\logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        main()
        status = "SUCCESS"
        code = 0
    except Exception as exc:
        status = "ERROR"
        code = 1
        error = type(exc).__name__ + ": " + str(exc)
    entry = {"at": datetime.now(timezone.utc).isoformat(), "status": status, "node_id": os.environ.get("NODE_ID", "node-02")}
    if code:
        entry["error"] = error
    with (log_dir / "outbound-worker-status.jsonl").open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps(entry, ensure_ascii=False))
    return code

if __name__ == "__main__":
    sys.exit(run())
