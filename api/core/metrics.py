"""Prometheus metrics registry (module-level: one per process).

Mandated surface: requests_total, request_duration_seconds,
requests_in_flight, provider_requests_total, provider_failures_total,
llm_latency_seconds, job_duration_seconds.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

requests_total = Counter("requests_total", "HTTP requests served.", ["route", "method", "status"])
request_duration_seconds = Histogram("request_duration_seconds", "HTTP request latency.", ["route"])
requests_in_flight = Gauge("requests_in_flight", "Requests currently being served.")
provider_requests_total = Counter(
    "provider_requests_total", "LLM provider calls.", ["provider", "model"]
)
provider_failures_total = Counter(
    "provider_failures_total", "Failed LLM provider calls.", ["provider", "model"]
)
llm_latency_seconds = Histogram("llm_latency_seconds", "LLM call latency.", ["provider", "model"])
job_duration_seconds = Histogram("job_duration_seconds", "Producer job duration.", ["job_type"])


def render_metrics() -> bytes:
    return generate_latest()


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST
