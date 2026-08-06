"""Producer job submission (async): update + update-all → 202 JobAccepted."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.core.ratelimit import rate_limiter
from api.core.security import authenticate
from api.models.errors import ErrorEnvelope
from api.models.request import ProducerUpdateAllRequest, ProducerUpdateRequest
from api.models.response import JobAccepted
from api.services.producer_jobs import ProducerJobService

router = APIRouter(tags=["Producer"])


def get_job_service(request: Request) -> ProducerJobService:
    return request.app.state.producer_jobs


@router.post(
    "/producer/update",
    status_code=202,
    response_model=JobAccepted,
    summary="Queue an asynchronous update of one tracked concept.",
    description="Returns immediately with a job id; poll /api/v1/jobs/{job_id} "
    "for status and results. dry_run validates without writing.",
    responses={
        401: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        429: {"model": ErrorEnvelope},
    },
)
@rate_limiter.limit(lambda: rate_limiter.producer_rule())
async def update_concept(
    request: Request,
    body: ProducerUpdateRequest,
    service: ProducerJobService = Depends(get_job_service),
    _caller: str | None = Depends(authenticate),
) -> JobAccepted:
    return service.submit_update(body)


@router.post(
    "/producer/update-all",
    status_code=202,
    response_model=JobAccepted,
    summary="Queue an asynchronous update of every tracked concept.",
    description="Continues past per-concept failures; worst exit code in result.",
    responses={401: {"model": ErrorEnvelope}, 429: {"model": ErrorEnvelope}},
)
@rate_limiter.limit(lambda: rate_limiter.producer_rule())
async def update_all(
    request: Request,
    body: ProducerUpdateAllRequest,
    service: ProducerJobService = Depends(get_job_service),
    _caller: str | None = Depends(authenticate),
) -> JobAccepted:
    return service.submit_update_all(body)
