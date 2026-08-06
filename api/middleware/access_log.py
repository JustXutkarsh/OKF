"""Access logging: one structured line per request, plus HTTP metrics.

Every request log carries: request_id, method, route, api_version,
status, latency_ms. Never logs keys, prompts, or question content.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.core.logging import StageTimer, log_event
from api.core.metrics import (
    request_duration_seconds,
    requests_in_flight,
    requests_total,
)


def api_version_of(path: str) -> str:
    return "v1" if path.startswith("/api/v1") else "-"


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        requests_in_flight.inc()
        route = request.url.path
        try:
            with StageTimer() as timer:
                response = await call_next(request)
        finally:
            requests_in_flight.dec()
        requests_total.labels(
            route=route, method=request.method, status=str(response.status_code)
        ).inc()
        request_duration_seconds.labels(route=route).observe(timer.duration_ms / 1000)
        log_event(
            "http.request",
            request_id=getattr(request.state, "request_id", "-"),
            method=request.method,
            route=route,
            api_version=api_version_of(route),
            status=response.status_code,
            latency_ms=timer.duration_ms,
        )
        return response
