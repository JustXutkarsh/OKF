"""POST /compare — side-by-side consumers via ComparisonService (HTTP only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from api.core.ratelimit import rate_limiter
from api.core.security import authenticate
from api.models.errors import ErrorEnvelope
from api.models.request import QuestionRequest
from api.services.comparison import ComparisonService

router = APIRouter(tags=["Comparison"])


def get_comparison_service(request: Request) -> ComparisonService:
    return request.app.state.comparison_service


@router.post(
    "/compare",
    summary="Run all registered consumers in parallel and merge deterministically.",
    description="Executes Consumer A and Consumer B concurrently (no extra LLM "
    "call), embeds both frozen contracts, and adds deterministic metadata: "
    "shared documents, shared sources, bundle-version agreement, provider/model.",
    responses={
        401: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        429: {"model": ErrorEnvelope},
        502: {"model": ErrorEnvelope},
    },
)
@rate_limiter.limit(lambda: rate_limiter.general_rule())
async def compare(
    request: Request,
    body: QuestionRequest,
    service: ComparisonService = Depends(get_comparison_service),
    _caller: str | None = Depends(authenticate),
) -> dict:
    return await service.compare(body.question.strip(), body.max_docs, request.state.request_id)
