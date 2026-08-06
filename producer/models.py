"""Pydantic models for producer data flow."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ConceptSpec(BaseModel):
    """One tracked concept from the human-authored registry."""

    id: str
    title: str
    resource: str
    tags: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    key_actors: list[str] = Field(default_factory=list)
    search_query: str
    lookback_days: int | None = None
    max_results: int | None = None


class Evidence(BaseModel):
    """One normalized search result: drafting evidence and bundle source."""

    title: str
    url: str
    published_date: str | None = None
    snippet: str = ""
    note: str = ""


class LLMDraft(BaseModel):
    """The only content the LLM is allowed to produce. No metadata, no URLs."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    development: str = Field(min_length=1)


class ProducerConfig(BaseModel):
    """Runtime configuration assembled from defaults, registry, and env."""

    bundle_path: Path
    registry_path: Path
    lookback_days: int
    max_results: int
    model: str
    llm_provider: str = "groq"
    request_timeout: int = 30
    log_level: str = "INFO"
    tavily_api_key: str | None = None
    groq_api_key: str | None = None
    openai_api_key: str | None = None


class RequestTelemetry(BaseModel):
    """Telemetry for one LLM call (own copy; additive, read-only for callers)."""

    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class DevelopmentEntry(BaseModel):
    """One dated entry in the Developments log. Never rewritten."""

    date: str
    text: str


class SourceEntry(BaseModel):
    """One structured source entry in the Sources section."""

    title: str
    url: str
    accessed: str
    note: str


class Document(BaseModel):
    """In-memory representation of one canonical OKF concept document."""

    schema_version: int | str = 1
    id: str
    type: str = "concept"
    title: str
    resource: str
    tags: list[str] = Field(default_factory=list)
    created_at: str
    last_updated: str
    confidence: str
    related: list[str] = Field(default_factory=list)
    summary: str = ""
    developments: list[DevelopmentEntry] = Field(default_factory=list)
    key_actors: list[str] = Field(default_factory=list)
    sources: list[SourceEntry] = Field(default_factory=list)
