from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_defs import DurableResumeWorkflow

STATE = {"status": "STARTING", "detail": None}
TASK_QUEUE = "dayong-stress-100"
TOTAL = 100


def emit_result() -> None:
    print("TEMPORAL_STRESS_RESULT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


async def run_probe() -> None:
    db_path = f"/tmp/dayong-temporal-stress-{os.getpid()}.db"
    started = time.monotonic()
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        async with await WorkflowEnvironment.start_local(dev_server_database_filename=db_path) as env:
            async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[DurableResumeWorkflow]):
                handles = []
                for i in range(TOTAL):
                    workflow_id = f"dayong-stress-100-{i:03d}"
                    handle = await env.client.start_workflow(
                        DurableResumeWorkflow.run,
                        f"STRESS-{i:03d}",
                        id=workflow_id,
                        task_queue=TASK_QUEUE,
                    )
                    handles.append(handle)

                await asyncio.gather(*(h.signal(DurableResumeWorkflow.release) for h in handles))
                results = await asyncio.wait_for(
                    asyncio.gather(*(h.result() for h in handles)),
                    timeout=60,
                )

        good = [r for r in results if r.get("state") == "RESUMED_AFTER_SERVER_RESTART"]
        unique_markers = {r.get("marker") for r in results}
        elapsed = round(time.monotonic() - started, 3)
        if len(good) != TOTAL or len(unique_markers) != TOTAL:
            raise RuntimeError(f"STRESS_MISMATCH:completed={len(good)},unique={len(unique_markers)}")

        STATE["status"] = "PASS"
        STATE["detail"] = {
            "submitted": TOTAL,
            "completed": len(good),
            "failed": TOTAL - len(good),
            "unique_markers": len(unique_markers),
            "duration_seconds": elapsed,
            "persistence": db_path,
            "result": "100_OF_100_COMPLETED",
        }
        emit_result()
    except Exception as exc:
        STATE["status"] = "FAIL"
        STATE["detail"] = {
            "error": type(exc).__name__,
            "message": str(exc),
            "duration_seconds": round(time.monotonic() - started, 3),
        }
        emit_result()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(STATE, ensure_ascii=False).encode("utf-8")
        self.send_response(200 if STATE["status"] == "PASS" else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    threading.Thread(target=lambda: asyncio.run(run_probe()), daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
