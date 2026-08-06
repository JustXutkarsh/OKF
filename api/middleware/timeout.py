"""Request timeout middleware: bounded wait, 504 envelope on expiry."""

from __future__ import annotations

import anyio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.core.errors import envelope


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        timeout = request.app.state.settings.request_timeout_seconds
        try:
            with anyio.fail_after(timeout):
                return await call_next(request)
        except TimeoutError:
            return envelope(
                504,
                "UPSTREAM_TIMEOUT",
                f"Request exceeded the {timeout}s timeout.",
                request.state.request_id,
            )
        except ExceptionGroup as group:
            # BaseHTTPMiddleware task groups wrap unhandled downstream errors;
            # domain errors already returned envelopes inside the app, so a
            # group reaching here is a genuine internal failure.
            first = group.exceptions[0] if group.exceptions else group
            import logging

            logging.getLogger("api").debug("unhandled error", exc_info=first)
            return envelope(
                500,
                "INTERNAL",
                "Unexpected internal error.",
                request.state.request_id,
            )
