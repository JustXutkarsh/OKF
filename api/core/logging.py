"""Structured logging for the API layer (key=value, request-correlated).

Never logs API keys, prompts, bundle contents, or full questions. Every
request-scoped log carries request_id; LLM completions log provider,
model, latency, and token usage.
"""

from __future__ import annotations

import logging
import sys
import time

logger = logging.getLogger("api")


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S"
    )
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    logger.handlers[:] = [handler]
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False


def log_event(event: str, **fields: object) -> None:
    suffix = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", event, suffix)


class StageTimer:
    def __init__(self) -> None:
        self.duration_ms = 0
        self._start = 0.0

    def __enter__(self) -> StageTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.duration_ms = round((time.perf_counter() - self._start) * 1000)
