from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any

from temporalio import activity

from models import DayongJob

FIRST_ATTEMPT_STARTED = asyncio.Event()


@activity.defn(name="DAYONG.ExecuteGovernedJob")
async def execute_governed_job(job: DayongJob) -> dict[str, Any]:
    allowed = {"MEDIA_PIPELINE_EXECUTE", "NODE_FUNCTIONAL_PROBE", "REPAIR_NODE"}
    if job.action not in allowed:
        raise ValueError(f"ACTION_NOT_ALLOWED:{job.action}")
    if job.authority_generation < 1:
        raise ValueError("INVALID_AUTHORITY_GENERATION")

    info = activity.info()
    activity.heartbeat({"phase": "accepted", "job_id": job.job_id, "attempt": info.attempt})

    mode = str(job.payload.get("mode", ""))
    if mode == "worker_handoff" and info.attempt == 1:
        FIRST_ATTEMPT_STARTED.set()
        while not activity.is_worker_shutdown():
            activity.heartbeat({"phase": "worker1_running", "job_id": job.job_id, "attempt": info.attempt})
            await asyncio.sleep(0.2)
        raise RuntimeError("FAULT_INJECTION_WORKER1_SHUTDOWN")

    if mode == "duplicate_guard":
        activity.heartbeat({"phase": "duplicate_guard_holding", "job_id": job.job_id, "attempt": info.attempt})
        await asyncio.sleep(2)

    fail_until = int(job.payload.get("fail_until_attempt", 0) or 0)
    if info.attempt <= fail_until:
        raise RuntimeError(f"FAULT_INJECTION_TRANSIENT_ATTEMPT_{info.attempt}")

    return {
        "job_id": job.job_id,
        "project_key": job.project_key,
        "action": job.action,
        "authority_generation": job.authority_generation,
        "iwu_id": job.iwu_id,
        "worker_identity": os.environ.get("DAYONG_WORKER_ID", "unknown"),
        "attempt": info.attempt,
        "payload_digest": hashlib.sha256(
            json.dumps(job.payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }
