from __future__ import annotations

import hashlib
import json
from typing import Any

from temporalio import activity

from models import DayongJob


def _validate(job: DayongJob) -> None:
    allowed = {"MEDIA_PIPELINE_EXECUTE", "NODE_FUNCTIONAL_PROBE", "REPAIR_NODE"}
    if job.action not in allowed:
        raise ValueError(f"ACTION_NOT_ALLOWED:{job.action}")
    if job.authority_generation < 1:
        raise ValueError("INVALID_AUTHORITY_GENERATION")


async def _execute(job: DayongJob, code_version: str) -> dict[str, Any]:
    _validate(job)
    info = activity.info()
    activity.heartbeat({"phase": "accepted", "job_id": job.job_id, "attempt": info.attempt, "code_version": code_version})
    return {
        "job_id": job.job_id,
        "project_key": job.project_key,
        "action": job.action,
        "authority_generation": job.authority_generation,
        "iwu_id": job.iwu_id,
        "attempt": info.attempt,
        "code_version": code_version,
        "payload_digest": hashlib.sha256(
            json.dumps(job.payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
    }


@activity.defn(name="DAYONG.ExecuteGovernedJob")
async def execute_governed_job_v1(job: DayongJob) -> dict[str, Any]:
    return await _execute(job, "v1")


@activity.defn(name="DAYONG.ExecuteGovernedJob")
async def execute_governed_job_v2(job: DayongJob) -> dict[str, Any]:
    return await _execute(job, "v2")
