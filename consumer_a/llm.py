"""Provider-configurable chat client and strict briefing parsing.

Provider and model come entirely from configuration (OKF_CONSUMER_A_*);
switching them never requires code changes. One call per question; a
malformed response aborts (no retry — the operator reruns). The parsing
guard rejects anything beyond plain reasoning JSON: code fences, markdown,
headings, YAML, URLs, citations, and unexpected fields.
"""

from __future__ import annotations

import json
import re
import threading
from typing import Any

from pydantic import ValidationError

from consumer_a.config import LLM_PROVIDERS
from consumer_a.exceptions import ConfigError, LLMResponseError
from consumer_a.exceptions import TimeoutError as ProviderTimeoutError
from consumer_a.models import Briefing, ConsumerConfig, RequestTelemetry

_CITATION_PATTERN = re.compile(r"\[\d+\]")


class ChatClient:
    """One OpenAI-compatible chat completion per question."""

    def __init__(self, config: ConsumerConfig) -> None:
        provider = config.provider
        settings = LLM_PROVIDERS.get(provider)
        if settings is None:  # load_config validates; guard direct construction
            raise ConfigError(
                f"Unsupported provider {provider!r}; supported: {sorted(LLM_PROVIDERS)}."
            )
        self._key_env = str(settings["key_env"])
        api_key = getattr(config, str(settings["key_attr"]))
        if not api_key:
            raise ConfigError(
                f"{self._key_env} is not set in the environment "
                f"(required for provider {provider!r})."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ConfigError("openai is not installed.") from exc

        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": config.request_timeout}
        if settings["base_url"]:
            kwargs["base_url"] = settings["base_url"]
        self._client = OpenAI(**kwargs)
        self._model = config.model
        self._provider = provider
        self._telemetry_tls = threading.local()

    @property
    def last_telemetry(self) -> RequestTelemetry | None:
        """Telemetry of the most recent call on THIS thread (read-only)."""

        return getattr(self._telemetry_tls, "telemetry", None)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """One chat completion; returns the raw text for parse_briefing."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            self._telemetry_tls.telemetry = RequestTelemetry(
                provider=self._provider, model=self._model, **(_extract_usage(response) or {})
            )
            content = response.choices[0].message.content
        except Exception as exc:
            text = f"{type(exc).__name__} {exc}".lower()
            if "timeout" in text or "timed out" in text:
                raise ProviderTimeoutError(
                    "LLM request timed out; retry later or raise OKF_REQUEST_TIMEOUT."
                ) from exc
            if "401" in text or "api key" in text or "authentication" in text:
                raise LLMResponseError(
                    f"LLM authentication failed; check {self._key_env}."
                ) from exc
            if "404" in text or "model_not_found" in text or "does not exist" in text:
                raise LLMResponseError(
                    f"LLM model {self._model!r} was not found on provider {self._provider!r}; "
                    f"check OKF_CONSUMER_A_MODEL or update provider model settings."
                ) from exc
            raise LLMResponseError(f"LLM call failed: {exc}") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("Malformed LLM response: empty content.")
        return content


def _extract_usage(response: object) -> dict:
    """Pull token usage off a chat-completions response (best effort)."""

    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def parse_briefing(content: object) -> Briefing:
    """Validate the LLM's raw text into a Briefing; abort on any violation."""

    if not isinstance(content, str) or not content.strip():
        raise LLMResponseError("Malformed LLM response: empty content.")

    text = content.strip()
    if text.startswith("```"):
        raise LLMResponseError("Malformed LLM response: remove the code fence.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Malformed LLM response: not JSON ({exc}).") from exc
    if not isinstance(payload, dict):
        raise LLMResponseError("Malformed LLM response: expected a JSON object.")

    try:
        briefing = Briefing(**payload)
    except ValidationError as exc:
        raise LLMResponseError(f"Malformed LLM response: bad briefing schema ({exc}).") from exc

    for text_field in (
        briefing.current_situation,
        briefing.reasoning,
        *briefing.key_developments,
        *briefing.key_actors,
    ):
        _reject_forbidden(text_field)
    return briefing


def _reject_forbidden(value: str) -> None:
    """One value must be plain prose: no URLs, citations, YAML, or headings."""

    if "http://" in value or "https://" in value or "www." in value:
        raise LLMResponseError("LLM output contains a URL or link; sources are Python-owned.")
    if _CITATION_PATTERN.search(value):
        raise LLMResponseError("LLM output contains a bracket citation; not permitted.")
    if "---" in value:
        raise LLMResponseError("LLM output contains a YAML frontmatter delimiter.")
    for line in value.splitlines():
        if line.lstrip().startswith("#"):
            raise LLMResponseError("LLM output contains a markdown heading.")
