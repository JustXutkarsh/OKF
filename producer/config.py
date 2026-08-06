"""Centralized producer configuration.

Precedence (highest first): process environment, .env file (development
convenience only), built-in defaults. All settings and both API keys flow
through load_config(); no module reads os.environ directly and no path is
hardcoded — every location can be overridden for deployment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import yaml
from pydantic import ValidationError

from producer.exceptions import ConfigError, RegistryError
from producer.models import ConceptSpec, ProducerConfig

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE_PATH = REPO_ROOT / "okf"
DEFAULT_REGISTRY_PATH = REPO_ROOT / "config" / "tracked_concepts.yaml"
DEFAULT_DOTENV_PATH = REPO_ROOT / ".env"

DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_MAX_RESULTS = 5
DEFAULT_LLM_PROVIDER = "groq"
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_LOG_LEVEL = "INFO"

ENV_BUNDLE_PATH = "OKF_BUNDLE_PATH"
ENV_REGISTRY_PATH = "OKF_REGISTRY_PATH"
ENV_MODEL = "OKF_PRODUCER_MODEL"
ENV_LLM_PROVIDER = "OKF_PRODUCER_LLM_PROVIDER"
ENV_LOOKBACK_DAYS = "OKF_LOOKBACK_DAYS"
ENV_MAX_RESULTS = "OKF_MAX_RESULTS"
ENV_REQUEST_TIMEOUT = "OKF_REQUEST_TIMEOUT"
ENV_LOG_LEVEL = "OKF_LOG_LEVEL"
ENV_TAVILY_KEY = "TAVILY_API_KEY"
ENV_GROQ_KEY = "GROQ_API_KEY"
ENV_OPENAI_KEY = "OPENAI_API_KEY"

# Supported LLM providers (generic OpenAI-compatible chat-completions
# APIs). Each maps to a base URL, the env var carrying its provider-
# specific key, the ProducerConfig attribute holding that key, and the
# provider's default model. Consumers A/B use the same convention from
# their own loaders; they never import this module. No vendor is
# hardcoded beyond this registry.
LLM_PROVIDERS: dict[str, dict[str, str | None]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": ENV_GROQ_KEY,
        "key_attr": "groq_api_key",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openai": {
        "base_url": None,
        "key_env": ENV_OPENAI_KEY,
        "key_attr": "openai_api_key",
        "default_model": "gpt-4o",
    },
}

# Deterministic confidence tiers (see updater.compute_confidence): the rule
# counts independent (unique-domain) sources in the merged Sources list.
#   >= CONFIDENCE_VERIFIED_MIN_INDEPENDENT -> "verified"
#   >= CONFIDENCE_MIXED_MIN_INDEPENDENT    -> "mixed"
#   otherwise                              -> "unverified"
CONFIDENCE_VERIFIED_MIN_INDEPENDENT = 3
CONFIDENCE_MIXED_MIN_INDEPENDENT = 2

REQUIRED_REGISTRY_FIELDS = ("id", "title", "resource", "search_query")


def load_config(
    bundle_path: str | Path | None = None,
    registry_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    dotenv_path: Path | None = DEFAULT_DOTENV_PATH,
) -> ProducerConfig:
    """Assemble configuration from env, optional .env, and defaults.

    Environment variables already set in the process always win over the
    .env file; .env exists for local development only and is gitignored.
    """

    environ: dict[str, str] = dict(os.environ) if env is None else dict(env)
    if dotenv_path is not None and dotenv_path.is_file():
        for key, value in _parse_dotenv(dotenv_path).items():
            environ.setdefault(key, value)

    llm_provider = environ.get(ENV_LLM_PROVIDER, DEFAULT_LLM_PROVIDER)
    if llm_provider not in LLM_PROVIDERS:
        raise ConfigError(
            f"Unsupported LLM provider {llm_provider!r} in {ENV_LLM_PROVIDER}; "
            f"supported: {', '.join(sorted(LLM_PROVIDERS))}"
        )
    model = environ.get(ENV_MODEL) or str(LLM_PROVIDERS[llm_provider]["default_model"])

    return ProducerConfig(
        bundle_path=Path(bundle_path or environ.get(ENV_BUNDLE_PATH) or DEFAULT_BUNDLE_PATH),
        registry_path=Path(
            registry_path or environ.get(ENV_REGISTRY_PATH) or DEFAULT_REGISTRY_PATH
        ),
        lookback_days=_int_setting(environ, ENV_LOOKBACK_DAYS, DEFAULT_LOOKBACK_DAYS),
        max_results=_int_setting(environ, ENV_MAX_RESULTS, DEFAULT_MAX_RESULTS),
        model=model,
        llm_provider=llm_provider,
        request_timeout=_int_setting(environ, ENV_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
        log_level=environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL),
        tavily_api_key=environ.get(ENV_TAVILY_KEY),
        groq_api_key=environ.get(ENV_GROQ_KEY),
        openai_api_key=environ.get(ENV_OPENAI_KEY),
    )


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file (comments, quotes, `export` ok)."""

    values: dict[str, str] = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key or not key.replace("_", "").isalnum():
            raise ConfigError(f"Invalid .env line {lineno} in {path}: {raw!r}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            # Unquoted trailing comments are stripped, matching dotenv tools.
            value = value.split(" #", 1)[0].rstrip()
        values[key] = value
    return values


def _int_setting(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def load_registry(path: Path) -> dict[str, ConceptSpec]:
    """Load and validate the human-authored tracked-concept registry."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RegistryError(f"Cannot load concept registry {path}: {exc}") from exc

    if not isinstance(raw, list) or not raw:
        raise RegistryError(f"Concept registry must be a non-empty YAML list: {path}")

    concepts: dict[str, ConceptSpec] = {}
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise RegistryError(f"Registry entry #{index} must be a mapping.")
        missing = [field for field in REQUIRED_REGISTRY_FIELDS if not item.get(field)]
        if missing:
            raise RegistryError(
                f"Registry entry #{index} is missing required fields: {', '.join(missing)}"
            )
        try:
            spec = ConceptSpec(**item)
        except ValidationError as exc:
            raise RegistryError(f"Registry entry #{index} is invalid: {exc}") from exc
        if spec.id in concepts:
            raise RegistryError(f"Duplicate concept id in registry: {spec.id}")
        concepts[spec.id] = spec
    return concepts


def get_concept(registry: dict[str, ConceptSpec], concept_id: str) -> ConceptSpec:
    """Return one concept from the registry or fail with a helpful message."""

    spec = registry.get(concept_id)
    if spec is None:
        known = ", ".join(sorted(registry)) or "(none)"
        raise RegistryError(f"Unknown concept `{concept_id}`. Registered concepts: {known}")
    return spec


def concept_relpath(spec: ConceptSpec) -> str:
    """Return the bundle-relative path for a concept document."""

    return f"{spec.resource}/{spec.id}.md"


def resolve_window(
    spec: ConceptSpec,
    config: ProducerConfig,
    lookback_days: int | None = None,
    max_results: int | None = None,
) -> tuple[int, int]:
    """Resolve search window: CLI override > per-concept override > default."""

    return (
        lookback_days or spec.lookback_days or config.lookback_days,
        max_results or spec.max_results or config.max_results,
    )
