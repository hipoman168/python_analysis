from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from activities import execute_governed_job
from models import DayongJob
from workflow_defs import DayongJobWorkflow

SOURCE_COMMIT = "ee93b76e5e7de0f2121d246c7654e89960608053"
STATE = {"status": "STARTING", "source_commit": SOURCE_COMMIT, "detail": None}


def emit_result() -> None:
    print("TEMPORAL_SMOKE_RESULT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


async def run_smoke() -> None:
    try:
        async with await WorkflowEnvironment.start_local() as env:
            async with Worker(
                env.client,
                task_queue="dayong-smoke",
                workflows=[DayongJobWorkflow],
                activities=[execute_governed_job],
            ):
                job = DayongJob(
                    job_id="SMOKE-TEMPORAL-DUP-001",
                    project_key="TEMPORAL_CORE",
                    action="NODE_FUNCTIONAL_PROBE",
                    authority_generation=1,
                    iwu_id="IWU-SMOKE-DUP-001",
                    payload={"mode": "duplicate_guard", "evidence_required": True},
                )
                workflow_id = "dayong-smoke-temporal-duplicate-001"
                handle = await env.client.start_workflow(
                    DayongJobWorkflow.run,
                    job,
                    id=workflow_id,
                    task_queue="dayong-smoke",
                )

                duplicate_error = None
                try:
                    await env.client.start_workflow(
                        DayongJobWorkflow.run,
                        job,
                        id=workflow_id,
                        task_queue="dayong-smoke",
                    )
                except Exception as exc:
                    duplicate_error = type(exc).__name__

                result = await asyncio.wait_for(handle.result(), timeout=30)
                if duplicate_error != "WorkflowAlreadyStartedError":
                    raise RuntimeError(f"DUPLICATE_GUARD_NOT_ENFORCED:{duplicate_error}")

                STATE["status"] = "PASS"
                STATE["detail"] = {
                    "job_id": result.job_id,
                    "state": result.state,
                    "workflow_id": workflow_id,
                    "duplicate_submission": "REJECTED",
                    "duplicate_error": duplicate_error,
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
