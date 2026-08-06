"""Pydantic models for Consumer B data flow."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ConsumerConfig(BaseModel):
    """Runtime configuration for Consumer B (own loader, own env vars)."""

    bundle_path: Path
    provider: str = "openai"
    model: str = "gpt-5.4-mini"
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
    schema_version: int | str = 1
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

    def searchable_text(self) -> str:
        """All prose the conflict verifier may match snippets against."""

        parts = [self.summary]
        parts.extend(entry.text for entry in self.developments)
        parts.extend(self.key_actors)
        return "\n".join(parts)


class ConflictClaim(BaseModel):
    """One conflicting-evidence claim as returned by the LLM.

    `documents` are 1-based indexes into the prompt's document list —
    the LLM never sees document ids. Python resolves and verifies these.
    """

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    documents: list[int] = Field(min_length=1)
    supporting_text: str = Field(min_length=1)
    conflicting_text: str = Field(min_length=1)


class CriticalAnalysis(BaseModel):
    """The only content the LLM is allowed to produce: analysis, no sources.

    Every field is required: the LLM must always return the complete
    object (empty lists are fine, missing keys are a contract violation).
    """

    model_config = ConfigDict(extra="forbid")

    assumptions: list[str]
    conflicting_evidence: list[ConflictClaim]
    uncertainties: list[str]
    alternative_interpretations: list[str]
    missing_information: list[str]
    confidence_assessment: str
    reasoning: str


class ResolvedConflict(BaseModel):
    """A conflict claim verified by Python against the bundle text."""

    description: str
    document_ids: list[str]
    supporting_text: str
    conflicting_text: str


class CriticalAnalysisReport(BaseModel):
    """Python-assembled analysis: verified conflicts, deterministic shape."""

    assumptions: list[str] = Field(default_factory=list)
    conflicting_evidence: list[ResolvedConflict] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    alternative_interpretations: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence_assessment: str = ""


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
    critical_analysis: CriticalAnalysisReport
    reasoning: str = ""
    documents_used: list[str] = Field(default_factory=list)
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    sources: list[ReportSource] = Field(default_factory=list)
    retrieval: RetrievalDiagnostics
    ranking: list[RankingEntry] = Field(default_factory=list)
    provider: str
    model: str
    generated_at: str
    # null unless every retrieved document agrees on one schema_version
    bundle_version: int | str | None = 1
