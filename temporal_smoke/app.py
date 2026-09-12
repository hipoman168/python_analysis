from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

SOURCE_COMMIT = "d5728f543b522fa3b3e641087c21b6bc55b50c44"
STATE = {"status": "STARTING", "source_commit": SOURCE_COMMIT, "detail": None}


@dataclass
class DayongJob:
    job_id: str
    project_key: str
    action: str
    authority_generation: int
    iwu_id: str
    payload: dict[str, Any]


@dataclass
class DayongResult:
    job_id: str
    state: str
    evidence: dict[str, Any]


@activity.defn(name="DAYONG.ExecuteGovernedJob")
async def execute_governed_job(job: DayongJob) -> dict[str, Any]:
    allowed = {"MEDIA_PIPELINE_EXECUTE", "NODE_FUNCTIONAL_PROBE", "REPAIR_NODE"}
    if job.action not in allowed:
        raise ValueError(f"ACTION_NOT_ALLOWED:{job.action}")
    if job.authority_generation < 1:
        raise ValueError("INVALID_AUTHORITY_GENERATION")
    activity.heartbeat({"phase": "accepted", "job_id": job.job_id})
    return {
        "job_id": job.job_id,
        "project_key": job.project_key,
        "action": job.action,
        "authority_generation": job.authority_generation,
        "iwu_id": job.iwu_id,
        "worker_identity": os.environ.get("DAYONG_WORKER_ID", "unknown"),
        "payload_digest": hashlib.sha256(
            json.dumps(job.payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


@workflow.defn(name="DAYONG.JobWorkflow")
class DayongJobWorkflow:
    @workflow.run
    async def run(self, job: DayongJob) -> DayongResult:
        evidence = await workflow.execute_activity(
            "DAYONG.ExecuteGovernedJob",
            job,
            start_to_close_timeout=timedelta(minutes=2),
            heartbeat_timeout=timedelta(seconds=20),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(seconds=10),
                maximum_attempts=3,
            ),
        )
        return DayongResult(job_id=job.job_id, state="COMPLETED", evidence=evidence)


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
                    job_id="SMOKE-TEMPORAL-001",
                    project_key="TEMPORAL_CORE",
                    action="NODE_FUNCTIONAL_PROBE",
                    authority_generation=1,
                    iwu_id="IWU-SMOKE-001",
                    payload={"mode": "smoke", "evidence_required": True},
                )
                result = await env.client.execute_workflow(
                    DayongJobWorkflow.run,
                    job,
                    id="dayong-smoke-temporal-core-001",
                    task_queue="dayong-smoke",
                )
                STATE["status"] = "PASS"
                STATE["detail"] = {
                    "job_id": result.job_id,
                    "state": result.state,
                    "evidence": result.evidence,
                }
    except Exception as exc:
        STATE["status"] = "FAIL"
        STATE["detail"] = {"error": type(exc).__name__, "message": str(exc)}


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
