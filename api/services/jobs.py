"""JobManager: asynchronous job lifecycle over a bounded thread pool.

Owns submission, status transitions, timestamps, result/error capture,
retention pruning, and graceful shutdown. In-memory by design (single
worker deployment); records are plain data, ready for a future durable
backend with no API change.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from api.core.errors import map_component_error
from api.core.logging import log_event
from api.core.metrics import job_duration_seconds
from api.models.response import JobRecord


class JobManager:
    def __init__(self, retention: int = 100, max_workers: int = 2) -> None:
        self._retention = retention
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="okf-job")

    def submit(self, job_type: str, fn: Callable[..., dict], *args: Any) -> JobRecord:
        record = JobRecord(
            job_id=uuid.uuid4().hex,
            job_type=job_type,
            status="pending",
            created_at=_now(),
        )
        with self._lock:
            self._jobs[record.job_id] = record
            self._order.append(record.job_id)
            self._prune_locked()
        log_event("job.submitted", job_id=record.job_id, job_type=job_type)
        self._executor.submit(self._run, record.job_id, fn, *args)
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 20) -> list[JobRecord]:
        with self._lock:
            ids = list(reversed(self._order))[:limit]
            return [self._jobs[job_id] for job_id in ids]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _run(self, job_id: str, fn: Callable[..., dict], *args: Any) -> None:
        self._transition(job_id, status="running", started_at=_now())
        started = time.perf_counter()
        try:
            result = fn(*args)
            self._transition(job_id, status="succeeded", finished_at=_now(), result=result)
        except Exception as exc:  # jobs must never crash the pool
            api_error = map_component_error(exc)
            error_payload: dict[str, Any] = {"code": api_error.code, "message": api_error.message}
            if api_error.details:
                error_payload.update(api_error.details)
            self._transition(
                job_id,
                status="failed",
                finished_at=_now(),
                error=error_payload,
            )
        record = self.get(job_id)
        assert record is not None  # submitted moments ago in submit()
        job_duration_seconds.labels(job_type=record.job_type).observe(time.perf_counter() - started)
        log_event("job.finished", job_id=job_id, status=record.status)

    def _transition(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(update=fields)

    def _prune_locked(self) -> None:
        while len(self._order) > self._retention:
            oldest = self._order[0]
            if self._jobs[oldest].status in ("pending", "running"):
                break
            self._order.pop(0)
            self._jobs.pop(oldest, None)


def _now() -> str:
    return datetime.now(UTC).isoformat()
