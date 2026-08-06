"""Outbound response models (backend-owned envelopes only).

Consumer answer payloads already have frozen contracts; they pass through
unchanged as embedded JSON — never remodeled here.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class JobAccepted(BaseModel):
    job_id: str
    job_type: str
    status: str
    created_at: str


class JobRecord(BaseModel):
    job_id: str
    job_type: str
    status: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class ReadyCheck(BaseModel):
    bundle_accessible: bool
    registry_loads: bool
    document_count: int
    consumers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    producer: dict[str, Any] = Field(default_factory=dict)


class ReadyResponse(BaseModel):
    status: str
    checks: ReadyCheck


class VersionResponse(BaseModel):
    app_version: str
    git_sha: str
    build_time: str
    bundle_version: int | str | None
    components: dict[str, str]
