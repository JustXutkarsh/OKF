"""Application factory for the OKF production API.

Lifespan owns: configuration validation, logger initialization, metrics,
RateLimiter initialization, ConsumerRegistry initialization, application
service construction, and JobManager construction. Shutdown stops the
JobManager and closes all pooled provider clients (no resource leaks).

Middleware order (deterministic, outermost → innermost):
    Request ID → Access Logging → Rate Limiting (at routes) → Timeout
    → Authentication (route dependencies) → Router.
Rate limiting is enforced per-route before the handler body but after
dependency authentication, and it is logged accordingly.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import API_VERSION_PREFIX, APISettings, load_settings
from api.core.errors import register_exception_handlers
from api.core.logging import configure_logging, log_event
from api.core.ratelimit import rate_limiter
from api.middleware.access_log import AccessLogMiddleware
from api.middleware.request_id import RequestIdMiddleware
from api.middleware.timeout import TimeoutMiddleware
from api.routers import analyze, brief, compare, jobs, producer, system
from api.services.analysis import AnalysisService
from api.services.briefing import BriefingService
from api.services.comparison import ComparisonService
from api.services.jobs import JobManager
from api.services.producer_jobs import ProducerJobService
from api.services.registry import build_default_registry


def create_app(settings: APISettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ---- configuration validation (fail fast) ----
        if not settings.auth_configured:
            raise RuntimeError(
                "OKF_API_KEYS is empty and OKF_API_AUTH_DISABLED is not set; "
                "refusing to start without an authentication decision."
            )

        # ---- registry, services, jobs ----
        registry = build_default_registry()
        jobs = JobManager(retention=settings.job_retention)

        app.state.settings = settings
        app.state.registry = registry
        app.state.jobs = jobs
        app.state.briefing_service = BriefingService(registry)
        app.state.analysis_service = AnalysisService(registry)
        app.state.comparison_service = ComparisonService(registry)
        app.state.producer_jobs = ProducerJobService(jobs)

        log_event(
            "api.started",
            app_version=settings.app_version,
            git_sha=settings.git_sha,
            auth="disabled" if settings.auth_disabled else "keys",
            consumers=[a.name for a in registry.all()],
        )
        yield

        # ---- graceful shutdown ----
        app.state.jobs.shutdown()
        for adapter in registry.all():
            client = adapter.client
            inner = getattr(client, "_client", None)
            if inner is not None and hasattr(inner, "close"):
                inner.close()
        log_event("api.stopped")

    app = FastAPI(
        title="OKF Geopolitics Knowledge API",
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Rate limiting must attach before the middleware stack is built
    # (lifespan would be too late for the 429 exception handler).
    rate_limiter.configure(settings)
    rate_limiter.attach(app)

    # Middleware: later additions run FIRST (outermost). Desired order:
    # RequestId → AccessLog → Timeout → router. CORS innermost.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimeoutMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    for module in (brief, analyze, compare, producer, jobs, system):
        app.include_router(module.router, prefix=API_VERSION_PREFIX)

    return app


app = create_app()
