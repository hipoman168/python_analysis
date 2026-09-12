from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from temporalio.api.workflowservice.v1 import (
    DescribeWorkerDeploymentRequest,
    SetWorkerDeploymentCurrentVersionRequest,
)
from temporalio.common import VersioningBehavior, WorkerDeploymentVersion
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker, WorkerDeploymentConfig

from activities import execute_governed_job_v1, execute_governed_job_v2
from models import DayongJob
from workflow_defs import DayongJobWorkflow

STATE = {"status": "STARTING", "detail": None}
DEPLOYMENT_NAME = "dayong-smoke-deployment"
TASK_QUEUE = "dayong-smoke-versioned"
V1 = WorkerDeploymentVersion(deployment_name=DEPLOYMENT_NAME, build_id="v1")
V2 = WorkerDeploymentVersion(deployment_name=DEPLOYMENT_NAME, build_id="v2")


def emit_result() -> None:
    print("TEMPORAL_VERSIONING_RESULT=" + json.dumps(STATE, ensure_ascii=False, sort_keys=True), flush=True)


async def describe(client):
    return await client.workflow_service.describe_worker_deployment(
        DescribeWorkerDeploymentRequest(namespace=client.namespace, deployment_name=DEPLOYMENT_NAME)
    )


async def set_current(client, version: WorkerDeploymentVersion) -> None:
    desc = await describe(client)
    await client.workflow_service.set_worker_deployment_current_version(
        SetWorkerDeploymentCurrentVersionRequest(
            namespace=client.namespace,
            deployment_name=DEPLOYMENT_NAME,
            version=version.to_canonical_string(),
            conflict_token=desc.conflict_token,
            identity=client.identity,
            ignore_missing_task_queues=False,
            allow_no_pollers=False,
        )
    )


async def run_job(client, suffix: str) -> str:
    job = DayongJob(
        job_id=f"SMOKE-VERSION-{suffix}",
        project_key="TEMPORAL_CORE",
        action="NODE_FUNCTIONAL_PROBE",
        authority_generation=1,
        iwu_id=f"IWU-VERSION-{suffix}",
        payload={"phase": suffix, "evidence_required": True},
    )
    result = await client.execute_workflow(
        DayongJobWorkflow.run,
        job,
        id=f"dayong-versioning-{suffix}",
        task_queue=TASK_QUEUE,
    )
    return str(result.evidence.get("code_version"))


async def run_probe() -> None:
    try:
        async with await WorkflowEnvironment.start_local() as env:
            worker1 = Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[DayongJobWorkflow],
                activities=[execute_governed_job_v1],
                deployment_config=WorkerDeploymentConfig(
                    version=V1,
                    use_worker_versioning=True,
                    default_versioning_behavior=VersioningBehavior.PINNED,
                ),
            )
            worker2 = Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[DayongJobWorkflow],
                activities=[execute_governed_job_v2],
                deployment_config=WorkerDeploymentConfig(
                    version=V2,
                    use_worker_versioning=True,
                    default_versioning_behavior=VersioningBehavior.PINNED,
                ),
            )
            t1 = asyncio.create_task(worker1.run())
            t2 = asyncio.create_task(worker2.run())
            await asyncio.sleep(2)

            await set_current(env.client, V1)
            phase_v1 = await run_job(env.client, "v1-current")
            await set_current(env.client, V2)
            phase_v2 = await run_job(env.client, "v2-current")
            await set_current(env.client, V1)
            phase_rollback = await run_job(env.client, "rollback-v1")

            await worker1.shutdown()
            await worker2.shutdown()
            await t1
            await t2

            if [phase_v1, phase_v2, phase_rollback] != ["v1", "v2", "v1"]:
                raise RuntimeError(f"VERSION_ROUTING_MISMATCH:{phase_v1},{phase_v2},{phase_rollback}")

            STATE["status"] = "PASS"
            STATE["detail"] = {
                "deployment": DEPLOYMENT_NAME,
                "sequence": [
                    {"current": "v1", "executed_by": phase_v1},
                    {"current": "v2", "executed_by": phase_v2},
                    {"rollback_current": "v1", "executed_by": phase_rollback},
                ],
                "result": "V1_TO_V2_TO_V1_ROLLBACK_PASS",
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
