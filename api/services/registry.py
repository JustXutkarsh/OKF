"""ConsumerRegistry: the backend never hardcodes Consumer A or B.

Each adapter wraps one consumer's public service interface. Adding a
future Consumer C = one adapter entry; routes and ComparisonService stay
untouched.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from api.core.errors import APIError


@dataclass(frozen=True)
class ConsumerAdapter:
    """One consumer behind a uniform backend-facing shape."""

    name: str  # "briefing" | "analysis" | ...
    json_key: str  # key in the /compare envelope
    method_name: str  # public service method: "answer" | "analyze"
    service: Any  # the consumer's ConsumerService (pooled client injected)
    route_hint: str  # "/brief" | "/analyze" (log correlation)
    provider: str
    model: str
    payload: Callable[[Any], dict]  # report -> frozen contract dict (consumer's own renderer)
    client: Any = None
    client_error: str | None = None


class ConsumerRegistry:
    """Lookup-only registry feeding application services."""

    def __init__(self, adapters: list[ConsumerAdapter]) -> None:
        self._by_name = {adapter.name: adapter for adapter in adapters}

    def get(self, name: str) -> ConsumerAdapter:
        adapter = self._by_name.get(name)
        if adapter is None:
            raise APIError(500, "INTERNAL", f"Unknown consumer {name!r} in registry.")
        return adapter

    def all(self) -> list[ConsumerAdapter]:
        return list(self._by_name.values())


def build_default_registry() -> ConsumerRegistry:
    """Construct adapters for the bundled consumers (imports stay lazy)."""

    from consumer_a.config import load_config as load_a
    from consumer_a.exceptions import ConfigError as AConfigError
    from consumer_a.llm import ChatClient as ChatClientA
    from consumer_a.renderer import render_json as render_a
    from consumer_a.service import ConsumerService as ServiceA
    from consumer_b.config import load_config as load_b
    from consumer_b.exceptions import ConfigError as BConfigError
    from consumer_b.llm import ChatClient as ChatClientB
    from consumer_b.renderer import render_json as render_b
    from consumer_b.service import ConsumerService as ServiceB

    def _adapter(
        name: str,
        json_key: str,
        method_name: str,
        route_hint: str,
        config: Any,
        client_cls: Any,
        service_cls: Any,
        render: Any,
        config_error_cls: Any,
    ) -> ConsumerAdapter:
        client = None
        client_error = None
        try:
            client = client_cls(config)  # pooled for the process lifetime
        except config_error_cls as exc:
            client_error = str(exc)  # readiness reports it; route 503s at call time
        return ConsumerAdapter(
            name=name,
            json_key=json_key,
            method_name=method_name,
            service=service_cls(config, llm_client=client),
            route_hint=route_hint,
            provider=config.provider,
            model=config.model,
            payload=lambda report: json.loads(render(report)),
            client=client,
            client_error=client_error,
        )

    return ConsumerRegistry(
        [
            _adapter(
                "briefing",
                "briefing",
                "answer",
                "/brief",
                load_a(),
                ChatClientA,
                ServiceA,
                render_a,
                AConfigError,
            ),
            _adapter(
                "analysis",
                "analysis",
                "analyze",
                "/analyze",
                load_b(),
                ChatClientB,
                ServiceB,
                render_b,
                BConfigError,
            ),
        ]
    )
