from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy, VersioningBehavior

from models import DayongJob, DayongResult


@workflow.defn(name="DAYONG.JobWorkflow", versioning_behavior=VersioningBehavior.PINNED)
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
