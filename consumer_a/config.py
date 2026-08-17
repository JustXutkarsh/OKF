"""Independent configuration loader for Consumer A.

Same convention as the producer (process env > .env dev fallback >
defaults) but deliberately a separate module: Consumer A shares nothing
with the producer except the okf/ directory on disk.

Provider/model are fully configurable:
    OKF_CONSUMER_A_PROVIDER=groq    (groq | openai)
    OKF_CONSUMER_A_MODEL=llama-3.3-70b-versatile
Switching providers or models never requires code changes.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from consumer_a.exceptions import ConfigError
from consumer_a.models import ConsumerConfig

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUNDLE_PATH = REPO_ROOT / "okf"
DEFAULT_DOTENV_PATH = REPO_ROOT / ".env"

DEFAULT_PROVIDER = "groq"
DEFAULT_MAX_DOCS = 3
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_LOG_LEVEL = "INFO"

ENV_PROVIDER = "OKF_CONSUMER_A_PROVIDER"
ENV_MODEL = "OKF_CONSUMER_A_MODEL"
ENV_MAX_DOCS = "OKF_CONSUMER_A_MAX_DOCS"
ENV_BUNDLE_PATH = "OKF_BUNDLE_PATH"
ENV_REQUEST_TIMEOUT = "OKF_REQUEST_TIMEOUT"
ENV_LOG_LEVEL = "OKF_LOG_LEVEL"
ENV_GROQ_KEY = "GROQ_API_KEY"
ENV_OPENAI_KEY = "OPENAI_API_KEY"

# Supported LLM providers (generic OpenAI-compatible chat-completions
# APIs). Duplicated by design: provider configuration must never be
# shared between the producer and the consumers.
LLM_PROVIDERS: dict[str, dict[str, str | None]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": ENV_GROQ_KEY,
        "key_attr": "groq_api_key",
        "default_model": "openai/gpt-oss-120b",
    },
    "openai": {
        "base_url": None,
        "key_env": ENV_OPENAI_KEY,
        "key_attr": "openai_api_key",
        "default_model": "gpt-4o",
    },
}


def load_config(
    bundle_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    dotenv_path: Path | None = DEFAULT_DOTENV_PATH,
) -> ConsumerConfig:
    """Assemble Consumer A configuration from env, optional .env, defaults."""

    environ: dict[str, str] = dict(os.environ) if env is None else dict(env)
    if dotenv_path is not None and dotenv_path.is_file():
        for key, value in _parse_dotenv(dotenv_path).items():
            environ.setdefault(key, value)

    provider = environ.get(ENV_PROVIDER, DEFAULT_PROVIDER)
    if provider not in LLM_PROVIDERS:
        raise ConfigError(
            f"Unsupported provider {provider!r} in {ENV_PROVIDER}; "
            f"supported: {', '.join(sorted(LLM_PROVIDERS))}"
        )
    model = environ.get(ENV_MODEL) or str(LLM_PROVIDERS[provider]["default_model"])

    return ConsumerConfig(
        bundle_path=Path(bundle_path or environ.get(ENV_BUNDLE_PATH) or DEFAULT_BUNDLE_PATH),
        provider=provider,
        model=model,
        max_docs=_int_setting(environ, ENV_MAX_DOCS, DEFAULT_MAX_DOCS),
        request_timeout=_int_setting(environ, ENV_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
        log_level=environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL),
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
