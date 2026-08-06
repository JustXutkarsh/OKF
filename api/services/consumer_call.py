"""Shared backend helper: invoke one consumer adapter with telemetry logging."""

from __future__ import annotations

from typing import Any

from api.core.errors import APIError
from api.core.logging import StageTimer, log_event
from api.core.metrics import (
    llm_latency_seconds,
    provider_failures_total,
    provider_requests_total,
)
from api.services.registry import ConsumerAdapter


def call_consumer(
    adapter: ConsumerAdapter,
    question: str,
    max_docs: int | None,
    request_id: str,
) -> tuple[dict, int, Any]:
    """Call the consumer's public method; return (payload, latency_ms, telemetry).

    Raises MISCONFIGURED (503) when the adapter's client never built.
    """

    if adapter.client_error is not None:
        raise APIError(503, "MISCONFIGURED", adapter.client_error)

    with StageTimer() as timer:
        try:
            report = getattr(adapter.service, adapter.method_name)(question, max_docs=max_docs)
        except Exception:
            provider_failures_total.labels(provider=adapter.provider, model=adapter.model).inc()
            raise
    provider_requests_total.labels(provider=adapter.provider, model=adapter.model).inc()
    llm_latency_seconds.labels(provider=adapter.provider, model=adapter.model).observe(
        timer.duration_ms / 1000
    )

    telemetry = adapter.client.last_telemetry if adapter.client is not None else None
    log_event(
        "consumer.complete",
        request_id=request_id,
        route=adapter.route_hint,
        api_version="v1",
        consumer=adapter.name,
        provider=adapter.provider,
        model=adapter.model,
        latency_ms=timer.duration_ms,
        prompt_tokens=getattr(telemetry, "prompt_tokens", None),
        completion_tokens=getattr(telemetry, "completion_tokens", None),
        total_tokens=getattr(telemetry, "total_tokens", None),
    )
    return adapter.payload(report), timer.duration_ms, telemetry
