"""Operational endpoints: health, readiness, version, metrics."""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import Response

from api.core.metrics import METRICS_CONTENT_TYPE, render_metrics
from api.models.response import ReadyCheck, ReadyResponse, VersionResponse

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="Liveness probe (process is running).",
    description="Always 200 when the server can answer.",
)
async def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness probe: bundle, registry, and provider configuration.",
    description="Validates bundle access, producer registry, and each consumer's "
    "provider+key configuration. 200 when ready, 503 otherwise. No provider calls.",
    response_model=ReadyResponse,
)
async def ready(request: Request) -> ReadyResponse | Response:
    # consumer_b's reader exposes schema_version (superset catalog shape)
    from consumer_b.reader import scan_catalog
    from producer.config import load_config as load_producer_config
    from producer.config import load_registry

    checks_ok = True
    document_count = 0
    bundle_accessible = False
    registry_loads = False

    registry = request.app.state.registry
    bundle_path = None
    for adapter in registry.all():
        bundle_path = adapter.service._config.bundle_path
        break

    try:
        catalog = scan_catalog(bundle_path) if bundle_path else []
        document_count = len(catalog)
        bundle_accessible = document_count > 0
    except Exception:
        bundle_accessible = False
    checks_ok &= bundle_accessible

    try:
        producer_config = load_producer_config()
        registry_loads = bool(load_registry(producer_config.registry_path))
    except Exception:
        registry_loads = False
    checks_ok &= registry_loads

    consumers: dict[str, dict] = {}
    for adapter in registry.all():
        consumers[adapter.name] = {
            "provider": adapter.provider,
            "model": adapter.model,
            "client_ready": adapter.client_error is None,
            **({"error": adapter.client_error} if adapter.client_error else {}),
        }
        checks_ok &= adapter.client_error is None

    try:
        from producer.config import LLM_PROVIDERS

        provider_key_attr = LLM_PROVIDERS[producer_config.llm_provider]["key_attr"]
        producer_ready = bool(producer_config.tavily_api_key) and bool(
            getattr(producer_config, str(provider_key_attr), None)
        )
    except Exception:
        producer_ready = False
    checks_ok &= producer_ready

    response = ReadyResponse(
        status="ready" if checks_ok else "not_ready",
        checks=ReadyCheck(
            bundle_accessible=bundle_accessible,
            registry_loads=registry_loads,
            document_count=document_count,
            consumers=consumers,
            producer={
                "configured": producer_ready,
                "search_key_configured": bool(
                    "producer_config" in dir() and producer_config.tavily_api_key
                ),
            },
        ),
    )
    if checks_ok:
        return response
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=503, content=response.model_dump())


@router.get(
    "/version",
    summary="Build and bundle version information.",
    description="app_version, git_sha, build_time come from environment; "
    "bundle_version from the bundle's own schema_version consensus.",
    response_model=VersionResponse,
)
async def version(request: Request) -> VersionResponse:
    from consumer_b.reader import scan_catalog

    settings = request.app.state.settings
    bundle_version = None
    registry = request.app.state.registry
    adapters = registry.all()
    bundle_path = adapters[0].service._config.bundle_path if adapters else None
    try:
        versions = (
            {entry.schema_version for entry in scan_catalog(bundle_path)} if bundle_path else set()
        )
        if len(versions) == 1:
            bundle_version = versions.pop()
    except Exception:
        bundle_version = None

    return VersionResponse(
        app_version=settings.app_version,
        git_sha=settings.git_sha,
        build_time=settings.build_time,
        bundle_version=bundle_version,
        components={
            "api": settings.app_version,
            "producer": _pkg_version("producer"),
            "consumer_a": _pkg_version("consumer_a"),
            "consumer_b": _pkg_version("consumer_b"),
        },
    )


@router.get(
    "/metrics",
    summary="Prometheus metrics exposition.",
    description="Standard Prometheus text format for scraping.",
)
async def metrics() -> Response:
    return Response(content=render_metrics(), media_type=METRICS_CONTENT_TYPE)


def _pkg_version(package: str) -> str:
    try:
        module = __import__(package)
        return str(getattr(module, "__version__", "unknown"))
    except Exception:
        return "unknown"
