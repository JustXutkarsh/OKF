"""BriefingService: application service for POST /brief."""

from __future__ import annotations

from api.services.consumer_call import call_consumer
from api.services.registry import ConsumerRegistry


class BriefingService:
    def __init__(self, registry: ConsumerRegistry) -> None:
        self._adapter = registry.get("briefing")

    def brief(self, question: str, max_docs: int | None, request_id: str) -> dict:
        payload, _, _ = call_consumer(self._adapter, question, max_docs, request_id)
        return payload
