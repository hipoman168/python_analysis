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
TASK_QUEUE = "dayong-stress-100-batched"
TOTAL = 100
BATCH_SIZE = 10


def emit_result() -> None:
    print("TEMPORAL_STRESS_RESULT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


async def run_probe() -> None:
    db_path = f"/tmp/dayong-temporal-stress-batched-{os.getpid()}.db"
    started = time.monotonic()
    completed_results = []
    submitted = 0
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        async with await WorkflowEnvironment.start_local(dev_server_database_filename=db_path) as env:
            async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[DurableResumeWorkflow]):
                for batch_start in range(0, TOTAL, BATCH_SIZE):
                    handles = []
                    for i in range(batch_start, min(batch_start + BATCH_SIZE, TOTAL)):
                        workflow_id = f"dayong-stress-batched-{i:03d}"
                        handle = await asyncio.wait_for(
                            env.client.start_workflow(
                                DurableResumeWorkflow.run,
                                f"STRESS-{i:03d}",
                                id=workflow_id,
                                task_queue=TASK_QUEUE,
                            ),
                            timeout=10,
                        )
                        handles.append(handle)
                        submitted += 1

                    await asyncio.wait_for(
                        asyncio.gather(*(h.signal(DurableResumeWorkflow.release) for h in handles)),
                        timeout=20,
                    )
                    batch_results = await asyncio.wait_for(
                        asyncio.gather(*(h.result() for h in handles)),
                        timeout=30,
                    )
                    completed_results.extend(batch_results)
                    print(
                        f"TEMPORAL_STRESS_PROGRESS=batch={batch_start // BATCH_SIZE + 1}/10 completed={len(completed_results)}",
                        flush=True,
                    )

        good = [r for r in completed_results if r.get("state") == "RESUMED_AFTER_SERVER_RESTART"]
        unique_markers = {r.get("marker") for r in completed_results}
        elapsed = round(time.monotonic() - started, 3)
        if len(good) != TOTAL or len(unique_markers) != TOTAL:
            raise RuntimeError(f"STRESS_MISMATCH:completed={len(good)},unique={len(unique_markers)}")

        STATE["status"] = "PASS"
        STATE["detail"] = {
            "submitted": submitted,
            "completed": len(good),
            "failed": TOTAL - len(good),
            "unique_markers": len(unique_markers),
            "batch_size": BATCH_SIZE,
            "batches": TOTAL // BATCH_SIZE,
            "duration_seconds": elapsed,
            "persistence": db_path,
            "result": "100_OF_100_COMPLETED",
        }
        emit_result()
    except Exception as exc:
        STATE["status"] = "FAIL"
        STATE["detail"] = {
            "submitted": submitted,
            "completed": len(completed_results),
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
