"""Pydantic models for Consumer A data flow."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ConsumerConfig(BaseModel):
    """Runtime configuration for Consumer A (own loader, own env vars)."""

    bundle_path: Path
    provider: str = "groq"
    model: str = "openai/gpt-oss-120b"
    max_docs: int = 3
    request_timeout: int = 30
    log_level: str = "INFO"
    groq_api_key: str | None = None
    openai_api_key: str | None = None


class RequestTelemetry(BaseModel):
    """Telemetry for one LLM call (own copy; additive, read-only for callers)."""

    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class CatalogEntry(BaseModel):
    """Frontmatter-only view of one bundle document (no body ever read)."""

    id: str
    title: str
    resource: str
    tags: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    confidence: str = ""
    relative_path: str


class RankingEntry(BaseModel):
    """Per-signal score breakdown for one positively-scored candidate."""

    document_id: str
    title_score: int
    tag_score: int
    id_score: int
    resource_score: int
    phrase_bonus: int
    total_score: int


class RetrievalDiagnostics(BaseModel):
    """Retrieval-stage diagnostics for the JSON contract."""

    candidate_count: int
    selected_count: int
    selected_documents: list[str] = Field(default_factory=list)
    retrieval_time_ms: int = 0


class RetrievalResult(BaseModel):
    """Internal retrieval outcome: selection plus the full ranking."""

    candidate_count: int
    selected: list[CatalogEntry] = Field(default_factory=list)
    ranking: list[RankingEntry] = Field(default_factory=list)


class DevelopmentEntry(BaseModel):
    """One dated entry in a document's Developments log."""

    date: str
    text: str


class SourceRef(BaseModel):
    """One source entry inside a bundle document."""

    title: str
    url: str
    accessed: str = ""
    note: str = ""


class BundleDocument(BaseModel):
    """One fully-read bundle document (only ever a SELECTED document)."""

    id: str
    title: str
    resource: str
    relative_path: str
    summary: str = ""
    developments: list[DevelopmentEntry] = Field(default_factory=list)
    key_actors: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class Briefing(BaseModel):
    """The only content the LLM is allowed to produce: reasoning, no sources."""

    model_config = ConfigDict(extra="forbid")

    current_situation: str = Field(min_length=1)
    key_developments: list[str] = Field(default_factory=list)
    key_actors: list[str] = Field(default_factory=list)
    reasoning: str


class EvidenceEntry(BaseModel):
    """Deterministic evidence: one section of one consulted document."""

    document_id: str
    section: str
    confidence: str
    matching_score: int


class ReportSource(BaseModel):
    """One deterministic source entry in the final answer."""

    document_id: str
    document_title: str
    source_title: str
    source_url: str
    accessed_date: str


class AnswerReport(BaseModel):
    """The complete deterministic answer, assembled by Python only.

    Mirrors the stable JSON contract consumed by the CLI today and the
    future backend API — the service returns this object, never text.
    """

    covered: bool
    answer: Briefing
    reasoning: str = ""
    documents_used: list[str] = Field(default_factory=list)
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    sources: list[ReportSource] = Field(default_factory=list)
    retrieval: RetrievalDiagnostics
    ranking: list[RankingEntry] = Field(default_factory=list)
    provider: str
    model: str
    generated_at: str
