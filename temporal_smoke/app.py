from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from activities import FIRST_ATTEMPT_STARTED, execute_governed_job
from models import DayongJob
from workflow_defs import DayongJobWorkflow

SOURCE_COMMIT = "f5e1783f469e5d6d74cb2d50b72ab4a9c4e39752"
STATE = {"status": "STARTING", "source_commit": SOURCE_COMMIT, "detail": None}


def emit_result() -> None:
    print("TEMPORAL_SMOKE_RESULT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


async def run_smoke() -> None:
    try:
        async with await WorkflowEnvironment.start_local() as env:
            worker1 = Worker(
                env.client,
                task_queue="dayong-smoke",
                workflows=[DayongJobWorkflow],
                activities=[execute_governed_job],
                graceful_shutdown_timeout=timedelta(seconds=2),
            )
            worker1_task = asyncio.create_task(worker1.run())

            job = DayongJob(
                job_id="SMOKE-TEMPORAL-HANDOFF-001",
                project_key="TEMPORAL_CORE",
                action="NODE_FUNCTIONAL_PROBE",
                authority_generation=1,
                iwu_id="IWU-SMOKE-HANDOFF-001",
                payload={
                    "mode": "worker_handoff",
                    "evidence_required": True,
                },
            )
            handle = await env.client.start_workflow(
                DayongJobWorkflow.run,
                job,
                id="dayong-smoke-temporal-handoff-001",
                task_queue="dayong-smoke",
            )

            await asyncio.wait_for(FIRST_ATTEMPT_STARTED.wait(), timeout=15)
            STATE["detail"] = {"phase": "worker1_started_then_shutdown"}
            await worker1.shutdown()
            await worker1_task

            worker2 = Worker(
                env.client,
                task_queue="dayong-smoke",
                workflows=[DayongJobWorkflow],
                activities=[execute_governed_job],
            )
            async with worker2:
                result = await asyncio.wait_for(handle.result(), timeout=30)

            STATE["status"] = "PASS"
            STATE["detail"] = {
                "job_id": result.job_id,
                "state": result.state,
                "handoff": "worker1_shutdown_to_worker2",
                "evidence": result.evidence,
            }
            emit_result()
    except Exception as exc:
        STATE["status"] = "FAIL"
        STATE["detail"] = {"error": type(exc).__name__, "message": str(exc)}
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
    threading.Thread(target=lambda: asyncio.run(run_smoke()), daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
