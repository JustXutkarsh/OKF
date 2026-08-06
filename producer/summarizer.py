"""Provider-configurable LLM drafting with strict JSON parsing.

One LLM call per concept run. No retries (cost rule): a malformed response
aborts the run and the operator reruns. The provider (groq | openai) and
model come from centralized config; both providers speak the
OpenAI-compatible chat-completions API. The LLM never emits URLs,
frontmatter, headings, or dates; parse_draft enforces that contract.
"""

from __future__ import annotations

import json
import threading
from typing import Any

from pydantic import ValidationError

from producer.config import LLM_PROVIDERS
from producer.exceptions import ConfigError, LLMResponseError
from producer.models import LLMDraft, ProducerConfig, RequestTelemetry


class Summarizer:
    """Draft summary + development prose via an OpenAI-compatible chat API."""

    def __init__(self, config: ProducerConfig) -> None:
        provider = config.llm_provider
        settings = LLM_PROVIDERS.get(provider)
        if settings is None:  # load_config validates; guard direct construction
            raise ConfigError(
                f"Unsupported LLM provider {provider!r}; supported: {sorted(LLM_PROVIDERS)}."
            )
        self._key_env = str(settings["key_env"])
        api_key = getattr(config, str(settings["key_attr"]))
        if not api_key:
            raise ConfigError(
                f"{self._key_env} is not set in the environment "
                f"(required for LLM provider {provider!r})."
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

    def draft(self, system_prompt: str, user_prompt: str) -> LLMDraft:
        """One chat completion returning a validated LLMDraft."""

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
            raise LLMResponseError(_friendly_error(exc, key_env=self._key_env)) from exc
        return parse_draft(content)


def _friendly_error(exc: Exception, *, key_env: str) -> str:
    """Turn client exceptions into actionable messages."""

    text = f"{type(exc).__name__} {exc}".lower()
    if "timeout" in text or "timed out" in text:
        return "LLM request timed out; retry later. Raise OKF_REQUEST_TIMEOUT if the model is slow."
    if "401" in text or "api key" in text or "authentication" in text:
        return f"LLM authentication failed; check {key_env} ({exc})."
    return f"LLM call failed: {exc}"


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


def parse_draft(content: object) -> LLMDraft:
    """Parse and guard the LLM's raw text into a validated LLMDraft.

    The LLM is allowed prose only: any URL, YAML delimiter, or markdown
    heading in the output is treated as a contract violation (abort).
    """

    if not isinstance(content, str) or not content.strip():
        raise LLMResponseError("Malformed LLM response: empty content.")

    text = _strip_code_fence(content.strip())
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"Malformed LLM response: not JSON ({exc}).") from exc
    if not isinstance(payload, dict):
        raise LLMResponseError("Malformed LLM response: expected a JSON object.")

    try:
        draft = LLMDraft(**payload)
    except ValidationError as exc:
        raise LLMResponseError(f"Malformed LLM response: bad draft schema ({exc}).") from exc

    for field_name, value in (("summary", draft.summary), ("development", draft.development)):
        _reject_forbidden(field_name, value)
    return draft


def _strip_code_fence(text: str) -> str:
    """Remove one surrounding ``` fence if the model added one."""

    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text


def _reject_forbidden(field_name: str, value: str) -> None:
    """Enforce the prose-only contract on one LLM output field."""

    if "http://" in value or "https://" in value:
        raise LLMResponseError(
            f"LLM {field_name} contains a URL; URLs must come from search evidence."
        )
    if "---" in value:
        raise LLMResponseError(f"LLM {field_name} contains a YAML frontmatter delimiter.")
    for line in value.splitlines():
        if line.lstrip().startswith("#"):
            raise LLMResponseError(f"LLM {field_name} contains a markdown heading.")
