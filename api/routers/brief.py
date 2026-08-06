"""POST /brief — Consumer A briefing via BriefingService (HTTP only)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request

from api.core.ratelimit import rate_limiter
from api.core.security import authenticate
from api.models.errors import ErrorEnvelope
from api.models.request import QuestionRequest
from api.services.briefing import BriefingService

router = APIRouter(tags=["Briefing"])


def get_briefing_service(request: Request) -> BriefingService:
    return request.app.state.briefing_service


@router.post(
    "/brief",
    summary="Answer a question as a structured briefing (Consumer A).",
    description="Grounded strictly in the OKF bundle; uncovers topics return the "
    "standard not-covered sentence. Returns Consumer A's frozen JSON contract.",
    responses={
        401: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        429: {"model": ErrorEnvelope},
        502: {"model": ErrorEnvelope},
    },
)
@rate_limiter.limit(lambda: rate_limiter.general_rule())
async def brief(
    request: Request,
    body: QuestionRequest,
    service: BriefingService = Depends(get_briefing_service),
    _caller: str | None = Depends(authenticate),
) -> dict:
    return await asyncio.to_thread(
        service.brief, body.question.strip(), body.max_docs, request.state.request_id
    )
