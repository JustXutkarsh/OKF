"""Inbound request models (strict pydantic validation)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Shared request shape for /brief, /analyze, /compare."""

    question: str = Field(min_length=1, max_length=2000)
    max_docs: int | None = Field(default=None, ge=1, le=10)


class ProducerUpdateRequest(BaseModel):
    concept_id: str = Field(min_length=1, max_length=200)
    lookback_days: int | None = Field(default=None, ge=1, le=90)
    max_results: int | None = Field(default=None, ge=1, le=20)
    dry_run: bool = False


class ProducerUpdateAllRequest(BaseModel):
    dry_run: bool = False
