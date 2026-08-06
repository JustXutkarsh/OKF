"""AnalysisService: application service for POST /analyze."""

from __future__ import annotations

from api.services.consumer_call import call_consumer
from api.services.registry import ConsumerRegistry


class AnalysisService:
    def __init__(self, registry: ConsumerRegistry) -> None:
        self._adapter = registry.get("analysis")

    def analyze(self, question: str, max_docs: int | None, request_id: str) -> dict:
        payload, _, _ = call_consumer(self._adapter, question, max_docs, request_id)
        return payload
