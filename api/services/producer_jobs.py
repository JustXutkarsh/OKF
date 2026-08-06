"""ProducerJobService: application service owning producer job submission.

Producer runs are long and mutating; they are jobs, not request/response.
The service builds fresh producer config per job (env-driven) and calls
the producer's public run functions — it never duplicates producer logic.
"""

from __future__ import annotations

from api.models.request import ProducerUpdateAllRequest, ProducerUpdateRequest
from api.models.response import JobAccepted, JobRecord
from api.services.jobs import JobManager


class ProducerJobService:
    def __init__(self, jobs: JobManager) -> None:
        self._jobs = jobs

    def submit_update(self, request: ProducerUpdateRequest) -> JobAccepted:
        record = self._jobs.submit("producer.update", self._run_update, request)
        return _accepted(record)

    def submit_update_all(self, request: ProducerUpdateAllRequest) -> JobAccepted:
        record = self._jobs.submit("producer.update_all", self._run_update_all, request)
        return _accepted(record)

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def list(self, limit: int = 20) -> list[JobRecord]:
        return self._jobs.list(limit)

    @staticmethod
    def _run_update(request: ProducerUpdateRequest) -> dict:
        from producer.cli import run

        report = run(
            request.concept_id,
            lookback_days=request.lookback_days,
            max_results=request.max_results,
            dry_run=request.dry_run,
        )
        return {"concept_id": request.concept_id, "dry_run": request.dry_run, "report": report}

    @staticmethod
    def _run_update_all(request: ProducerUpdateAllRequest) -> dict:
        from producer.cli import load_config, run_all

        reports, worst_code = run_all(config=load_config(), dry_run=request.dry_run)
        return {"dry_run": request.dry_run, "reports": reports, "worst_exit_code": worst_code}


def _accepted(record: JobRecord) -> JobAccepted:
    return JobAccepted(
        job_id=record.job_id,
        job_type=record.job_type,
        status=record.status,
        created_at=record.created_at,
    )
