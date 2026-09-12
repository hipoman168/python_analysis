from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflow_defs import DurableResumeWorkflow

STATE = {"status": "STARTING", "detail": None}
TASK_QUEUE = "dayong-durable-restart"
WORKFLOW_ID = "dayong-durable-restart-001"


def emit_result() -> None:
    print("TEMPORAL_RESTART_RESULT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


async def run_probe() -> None:
    db_path = f"/tmp/dayong-temporal-persist-{os.getpid()}.db"
    try:
        if os.path.exists(db_path):
            os.remove(db_path)

        env1 = await WorkflowEnvironment.start_local(dev_server_database_filename=db_path)
        worker1 = Worker(env1.client, task_queue=TASK_QUEUE, workflows=[DurableResumeWorkflow])
        worker1_task = asyncio.create_task(worker1.run())

        await env1.client.start_workflow(
            DurableResumeWorkflow.run,
            "PERSISTENCE-MARKER-001",
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE,
        )
        await asyncio.sleep(1)

        await worker1.shutdown()
        await worker1_task
        await env1.shutdown()

        if not os.path.exists(db_path):
            raise RuntimeError("PERSISTENCE_DB_NOT_CREATED")

        env2 = await WorkflowEnvironment.start_local(dev_server_database_filename=db_path)
        worker2 = Worker(env2.client, task_queue=TASK_QUEUE, workflows=[DurableResumeWorkflow])
        worker2_task = asyncio.create_task(worker2.run())

        handle2 = env2.client.get_workflow_handle(WORKFLOW_ID)
        await handle2.signal(DurableResumeWorkflow.release)
        result = await asyncio.wait_for(handle2.result(), timeout=30)

        await worker2.shutdown()
        await worker2_task
        await env2.shutdown()

        if result.get("state") != "RESUMED_AFTER_SERVER_RESTART":
            raise RuntimeError(f"UNEXPECTED_RESULT:{result}")

        STATE["status"] = "PASS"
        STATE["detail"] = {
            "workflow_id": WORKFLOW_ID,
            "database_file": db_path,
            "server_restart": "A_TO_B",
            "workflow_recreated": False,
            "result": result,
        }
        emit_result()
    except Exception as exc:
        STATE["status"] = "FAIL"
        STATE["detail"] = {"error": type(exc).__name__, "message": str(exc), "database_file": db_path}
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
