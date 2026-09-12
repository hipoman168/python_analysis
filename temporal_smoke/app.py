from __future__ import annotations

import asyncio
import inspect
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.api.workflowservice.v1 import (
    DescribeWorkerDeploymentRequest,
    SetWorkerDeploymentCurrentVersionRequest,
    SetWorkerDeploymentManagerRequest,
)
from temporalio.common import WorkerDeploymentVersion
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import WorkerDeploymentConfig

STATE = {"status": "STARTING", "detail": None}


def emit_result() -> None:
    print("TEMPORAL_VERSIONING_INTROSPECT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


def proto_fields(cls):
    return [f.name for f in cls.DESCRIPTOR.fields]


async def run_probe() -> None:
    try:
        async with await WorkflowEnvironment.start_local() as env:
            STATE["status"] = "PASS"
            STATE["detail"] = {
                "worker_deployment_config_signature": str(inspect.signature(WorkerDeploymentConfig)),
                "worker_deployment_version_signature": str(inspect.signature(WorkerDeploymentVersion)),
                "describe_fields": proto_fields(DescribeWorkerDeploymentRequest),
                "set_current_fields": proto_fields(SetWorkerDeploymentCurrentVersionRequest),
                "set_manager_fields": proto_fields(SetWorkerDeploymentManagerRequest),
                "namespace": env.client.namespace,
                "identity": env.client.identity,
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
    threading.Thread(target=lambda: asyncio.run(run_probe()), daemon=True).start()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), Handler).serve_forever()
