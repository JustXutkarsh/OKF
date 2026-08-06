"""Job inspection: list recent jobs and fetch one record."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.core.errors import APIError
from api.core.security import authenticate
from api.models.errors import ErrorEnvelope
from api.models.response import JobRecord
from api.services.producer_jobs import ProducerJobService

router = APIRouter(tags=["Jobs"])


def get_job_service(request: Request) -> ProducerJobService:
    return request.app.state.producer_jobs


@router.get(
    "/jobs",
    summary="List recent producer jobs (newest first).",
    description="Statuses: pending, running, succeeded, failed (cancelled reserved).",
    response_model=list[JobRecord],
)
async def list_jobs(
    limit: int = 20,
    service: ProducerJobService = Depends(get_job_service),
    _caller: str | None = Depends(authenticate),
) -> list[JobRecord]:
    return service.list(limit)


@router.get(
    "/jobs/{job_id}",
    summary="Fetch one job record by id.",
    description="Includes timestamps, result payload, or mapped error details.",
    response_model=JobRecord,
    responses={404: {"model": ErrorEnvelope}},
)
async def get_job(
    job_id: str,
    service: ProducerJobService = Depends(get_job_service),
    _caller: str | None = Depends(authenticate),
) -> JobRecord:
    record = service.get(job_id)
    if record is None:
        raise APIError(404, "JOB_NOT_FOUND", f"No job with id {job_id}.")
    return record
