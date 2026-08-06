"""Structured, secret-free logging and stage timing for producer runs.

Log lines go to stderr as `event key=value ...`; stdout stays reserved for
the human-readable run report. No API key or other secret is ever logged.
"""

from __future__ import annotations

import logging
import sys
import time

logger = logging.getLogger("producer")


def configure_logging(level: str = "INFO") -> None:
    """Configure the producer logger (UTC timestamps, stderr)."""

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
    """Emit one structured log line: `event key=value ...`."""

    suffix = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", event, suffix)


class StageTimer:
    """Measure one pipeline stage; elapsed time in milliseconds."""

    def __init__(self) -> None:
        self.duration_ms = 0
        self._start = 0.0

    def __enter__(self) -> StageTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.duration_ms = self.elapsed_ms()

    def elapsed_ms(self) -> int:
        return round((time.perf_counter() - self._start) * 1000)
