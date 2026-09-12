from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from temporalio import activity

from .models import DayongJob


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
