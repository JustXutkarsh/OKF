"""POST /analyze — Consumer B critical analysis via AnalysisService (HTTP only)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request

from api.core.ratelimit import rate_limiter
from api.core.security import authenticate
from api.models.errors import ErrorEnvelope
from api.models.request import QuestionRequest
from api.services.analysis import AnalysisService

router = APIRouter(tags=["Analysis"])


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


@router.post(
    "/analyze",
    summary="Critically analyze a question against the bundle (Consumer B).",
    description="Surfaces assumptions, conflicts, uncertainties, alternative "
    "interpretations, and information gaps. Returns Consumer B's frozen contract.",
    responses={
        401: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        429: {"model": ErrorEnvelope},
        502: {"model": ErrorEnvelope},
    },
)
@rate_limiter.limit(lambda: rate_limiter.general_rule())
async def analyze(
    request: Request,
    body: QuestionRequest,
    service: AnalysisService = Depends(get_analysis_service),
    _caller: str | None = Depends(authenticate),
) -> dict:
    return await asyncio.to_thread(
        service.analyze, body.question.strip(), body.max_docs, request.state.request_id
    )
