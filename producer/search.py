"""Thin wrapper over the Tavily search API.

Deliberately minimal: send one query, return the raw result items.
Normalization, deduplication, and ranking live in evidence.py.
"""

from __future__ import annotations

from typing import Any

from producer.exceptions import ConfigError, SearchError
from producer.models import ProducerConfig


class TavilySearch:
    """Fetch recent results for one query via the Tavily SDK."""

    def __init__(self, config: ProducerConfig) -> None:
        if not config.tavily_api_key:
            raise ConfigError("TAVILY_API_KEY is not set in the environment.")
        try:
            from tavily import TavilyClient
        except ImportError as exc:
            raise ConfigError("tavily-python is not installed.") from exc
        self._client = TavilyClient(api_key=config.tavily_api_key)

    def search(self, query: str, lookback_days: int, max_results: int) -> list[dict[str, Any]]:
        """Return raw Tavily result items for the given window.

        Raises SearchError on provider failure or a malformed response body.
        An empty result list is NOT an error; the caller treats it as a no-op.
        """

        try:
            response = self._client.search(
                query=query,
                days=lookback_days,
                max_results=max_results,
            )
        except Exception as exc:  # provider/network errors are opaque by design
            raise SearchError(_friendly_error(exc)) from exc

        if not isinstance(response, dict) or not isinstance(response.get("results"), list):
            raise SearchError(
                "Malformed Tavily response: expected an object with a 'results' list."
            )
        return response["results"]


def _friendly_error(exc: Exception) -> str:
    """Turn provider exceptions into actionable messages."""

    text = f"{type(exc).__name__} {exc}".lower()
    if "timeout" in text or "timed out" in text:
        return "Tavily search timed out; check connectivity or retry later."
    return f"Tavily search failed: {exc}"
