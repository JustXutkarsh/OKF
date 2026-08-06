"""ComparisonService: deterministic merge of every registered consumer.

All deterministic comparison logic lives HERE (not in routers): run every
registered consumer in parallel, embed their frozen contracts unchanged,
and assemble fixed-shape comparison metadata. No LLM call, no inference.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime

from api.services.consumer_call import call_consumer
from api.services.registry import ConsumerRegistry


class ComparisonService:
    def __init__(self, registry: ConsumerRegistry) -> None:
        self._adapters = registry.all()
        self._registry = registry

    async def compare(self, question: str, max_docs: int | None, request_id: str) -> dict:
        """Run all consumers concurrently; merge deterministically."""

        async def run_one(name: str):
            adapter = self._registry.get(name)
            payload, latency, _ = await asyncio.to_thread(
                call_consumer, adapter, question, max_docs, request_id
            )
            return name, adapter, payload, latency

        results = await asyncio.gather(*(run_one(a.name) for a in self._adapters))

        envelope: dict = {
            "question": question.strip(),
            "question_hash": hashlib.sha1(question.encode("utf-8")).hexdigest()[:10],
            "generated_at": datetime.now(UTC).isoformat(),
        }
        durations: dict[str, int] = {}
        documents_used: dict[str, set] = {}
        bundle_versions: dict[str, object] = {}
        providers: dict[str, dict] = {}
        for name, adapter, payload, latency in results:
            envelope[adapter.json_key] = payload
            durations[name] = latency
            documents_used[name] = set(payload.get("documents_used", []))
            bundle_versions[name] = payload.get("bundle_version")
            providers[name] = {"provider": adapter.provider, "model": adapter.model}

        shared = sorted(set.intersection(*documents_used.values())) if documents_used else []
        source_sets: dict[str, set] = {}
        for name, adapter, payload, latency in results:
            source_sets[name] = {
                str(source.get("source_url", ""))
                for source in payload.get("sources", [])
                if source.get("source_url")
            }
        shared_sources = sorted(set.intersection(*source_sets.values())) if source_sets else []
        versions = {v for v in bundle_versions.values() if v is not None}
        envelope["comparison"] = {
            "consumers": providers,
            "shared_documents": shared,
            "shared_sources": shared_sources,
            "bundle_versions": bundle_versions,
            "bundle_versions_agree": len(versions) <= 1,
            "durations_ms": durations,
        }
        return envelope
