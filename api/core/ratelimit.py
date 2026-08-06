"""Production-grade rate limiting: our RateLimiter wrapping slowapi.

Callers (routers, app factory) depend only on this abstraction — the
underlying engine (slowapi/limits) can be swapped without touching
routes or tests. Identity: bearer-token hash when present, else client IP.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.core.config import APISettings, hash_api_key
from api.core.errors import envelope


class RateLimiter:
    """Owns the limiter engine, route decorators, and the 429 handler.

    One module-level instance exists (rate_limiter below); routers bind
    decorators to it at import time, with rule strings evaluated lazily
    per request so env-driven settings apply after lifespan configure().
    """

    def __init__(self, settings: APISettings | None = None) -> None:
        self.settings = settings or APISettings()
        self._engine = Limiter(key_func=self._identify)

    def configure(self, settings: APISettings) -> None:
        """Wire real settings in during lifespan (engine identity stable)."""

        self.settings = settings

    @staticmethod
    def _identify(request: Request) -> str:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            return "key:" + hash_api_key(header[7:].strip())[:16]
        return get_remote_address(request) or "unknown"

    def limit(self, rule: str | Callable[[], str]) -> Callable:
        """Route decorator enforcing one rule, e.g. limiter.limit("60/minute").

        Accepts a lazy callable so env-configured rules resolve per request.
        """

        return self._engine.limit(rule)

    def general_rule(self) -> str:
        return self.settings.rate_limit

    def producer_rule(self) -> str:
        return self.settings.producer_rate_limit

    def attach(self, app: FastAPI) -> None:
        app.state.rate_limiter = self

        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
            return envelope(
                429,
                "RATE_LIMITED",
                f"Rate limit exceeded ({exc.detail}).",
                request.state.request_id,
            )


# Shared instance: imported by routers (decorators) and configured by lifespan.
rate_limiter = RateLimiter()
