"""API configuration: fully environment-driven (12-factor).

API keys are NEVER stored in plaintext: only their SHA-256 hashes live in
settings, and only hash prefixes ever appear in logs.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DOTENV_PATH = REPO_ROOT / ".env"

ENV_API_KEYS = "OKF_API_KEYS"
ENV_AUTH_DISABLED = "OKF_API_AUTH_DISABLED"
ENV_HOST = "OKF_API_HOST"
ENV_PORT = "OKF_API_PORT"
ENV_TIMEOUT = "OKF_API_REQUEST_TIMEOUT_SECONDS"
ENV_RATE_LIMIT = "OKF_API_RATE_LIMIT"
ENV_PRODUCER_RATE_LIMIT = "OKF_API_PRODUCER_RATE_LIMIT"
ENV_CORS = "OKF_API_CORS_ORIGINS"
ENV_APP_VERSION = "OKF_API_VERSION"
ENV_GIT_SHA = "OKF_API_GIT_SHA"
ENV_BUILD_TIME = "OKF_API_BUILD_TIME"
ENV_JOB_RETENTION = "OKF_API_JOB_RETENTION"
ENV_LOG_LEVEL = "OKF_LOG_LEVEL"

API_VERSION_PREFIX = "/api/v1"


def hash_api_key(token: str) -> str:
    """One-way hash of an API key; the only form stored or logged."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class APISettings(BaseModel):
    """Runtime settings assembled from env (+ .env dev fallback)."""

    host: str = "0.0.0.0"
    port: int = 8000
    request_timeout_seconds: int = 60
    rate_limit: str = "60/minute"
    producer_rate_limit: str = "5/minute"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_key_hashes: set[str] = Field(default_factory=set)
    auth_disabled: bool = False
    app_version: str = "1.0.0"
    git_sha: str = "unknown"
    build_time: str = "unknown"
    job_retention: int = 100
    log_level: str = "INFO"
    dotenv_path: Path | None = DEFAULT_DOTENV_PATH

    @property
    def auth_configured(self) -> bool:
        return self.auth_disabled or bool(self.api_key_hashes)


def load_settings(
    env: Mapping[str, str] | None = None, dotenv_path: Path | None = DEFAULT_DOTENV_PATH
) -> APISettings:
    """Build settings; plaintext keys are hashed immediately and discarded."""

    environ: dict[str, str] = dict(os.environ) if env is None else dict(env)
    if dotenv_path is not None and dotenv_path.is_file():
        for key, value in _parse_dotenv(dotenv_path).items():
            environ.setdefault(key, value)

    raw_keys = environ.get(ENV_API_KEYS, "")
    return APISettings(
        host=environ.get(ENV_HOST, "0.0.0.0"),
        port=_int(environ, ENV_PORT, 8000),
        request_timeout_seconds=_int(environ, ENV_TIMEOUT, 60),
        rate_limit=environ.get(ENV_RATE_LIMIT, "60/minute"),
        producer_rate_limit=environ.get(ENV_PRODUCER_RATE_LIMIT, "5/minute"),
        cors_origins=[o.strip() for o in environ.get(ENV_CORS, "*").split(",") if o.strip()],
        api_key_hashes={hash_api_key(k.strip()) for k in raw_keys.split(",") if k.strip()},
        auth_disabled=environ.get(ENV_AUTH_DISABLED, "").lower() in ("1", "true", "yes"),
        app_version=environ.get(ENV_APP_VERSION, "1.0.0"),
        git_sha=environ.get(ENV_GIT_SHA, "unknown"),
        build_time=environ.get(ENV_BUILD_TIME, "unknown"),
        job_retention=_int(environ, ENV_JOB_RETENTION, 100),
        log_level=environ.get(ENV_LOG_LEVEL, "INFO"),
    )


def _int(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file (comments, quotes, `export` ok)."""

    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values
