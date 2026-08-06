"""ConsumerService: the sole orchestration layer and public interface.

Flow: question → scan catalog → retrieve → NOT_COVERED short-circuit →
read selected documents (only) → LLM → validate JSON → Python builds
Sources and Evidence → AnswerReport.

answer() returns an AnswerReport object, never formatted text: the CLI
renders it for the console today; a future backend API will serialize the
same object to JSON — no business-logic changes required.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from consumer_a import NOT_COVERED_SENTENCE, prompts
from consumer_a.exceptions import RetrievalError
from consumer_a.llm import ChatClient, parse_briefing
from consumer_a.models import (
    AnswerReport,
    Briefing,
    BundleDocument,
    ConsumerConfig,
    EvidenceEntry,
    ReportSource,
    RetrievalDiagnostics,
    RetrievalResult,
)
from consumer_a.observability import StageTimer, log_event
from consumer_a.reader import read_documents, scan_catalog
from consumer_a.retriever import select

BRIEFING_SECTIONS = ("Summary", "Developments", "Key Actors")


class ConsumerService:
    """Orchestrates question answering. Public interface: answer()."""

    def __init__(
        self,
        config: ConsumerConfig,
        llm_client: Any = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._llm_client = llm_client
        self._clock = clock or (lambda: datetime.now(UTC))

    def answer(self, question: str, max_docs: int | None = None) -> AnswerReport:
        """Answer one question strictly from the bundle."""

        if not question or not question.strip():
            raise RetrievalError("Question must not be empty.")

        config = self._config
        limit = max_docs or config.max_docs
        question_hash = hashlib.sha1(question.encode("utf-8")).hexdigest()[:10]
        log_event("ask.start", question_hash=question_hash, question_len=len(question))

        with StageTimer() as total:
            with StageTimer() as stage:
                catalog = scan_catalog(config.bundle_path)
                retrieval = select(catalog, question, limit)
            log_event(
                "stage",
                stage="retrieve",
                duration_ms=stage.duration_ms,
                candidates=retrieval.candidate_count,
                selected=[entry.id for entry in retrieval.selected],
            )
            diagnostics = RetrievalDiagnostics(
                candidate_count=retrieval.candidate_count,
                selected_count=len(retrieval.selected),
                selected_documents=[entry.id for entry in retrieval.selected],
                retrieval_time_ms=stage.duration_ms,
            )

            if not retrieval.selected:
                # Not covered: never call the LLM (cost rule).
                report = self._build_report(None, [], retrieval, diagnostics)
                log_event(
                    "ask.complete",
                    question_hash=question_hash,
                    outcome="not-covered",
                    total_ms=total.elapsed_ms(),
                )
                return report

            with StageTimer() as stage:
                documents = read_documents(config.bundle_path, retrieval.selected)
            log_event(
                "stage",
                stage="read",
                duration_ms=stage.duration_ms,
                documents=len(documents),
            )

            client = self._llm_client or ChatClient(config)
            user_prompt = prompts.build_user_prompt(question, documents)
            with StageTimer() as stage:
                raw = client.chat(prompts.SYSTEM_PROMPT, user_prompt)
            briefing = parse_briefing(raw)
            log_event("stage", stage="llm", duration_ms=stage.duration_ms)

            covered = briefing.current_situation.strip() != NOT_COVERED_SENTENCE
            report = self._build_report(
                briefing if covered else None, documents, retrieval, diagnostics
            )
            log_event(
                "ask.complete",
                question_hash=question_hash,
                outcome="covered" if covered else "not-covered",
                total_ms=total.elapsed_ms(),
            )
            return report

    def _build_report(
        self,
        briefing: Briefing | None,
        documents: list[BundleDocument],
        retrieval: RetrievalResult,
        diagnostics: RetrievalDiagnostics,
    ) -> AnswerReport:
        """Python-only assembly of sources, evidence, and the final report."""

        covered = briefing is not None
        confidence_by_id = {entry.id: entry.confidence for entry in retrieval.selected}
        score_by_id = {row.document_id: row.total_score for row in retrieval.ranking}

        evidence = [
            EvidenceEntry(
                document_id=doc.id,
                section=section,
                confidence=confidence_by_id.get(doc.id, ""),
                matching_score=score_by_id.get(doc.id, 0),
            )
            for doc in documents
            for section, present in (
                ("Summary", bool(doc.summary)),
                ("Developments", bool(doc.developments)),
                ("Key Actors", bool(doc.key_actors)),
            )
            if present
        ]
        sources = [
            ReportSource(
                document_id=doc.id,
                document_title=doc.title,
                source_title=source.title,
                source_url=source.url,
                accessed_date=source.accessed,
            )
            for doc in documents
            for source in doc.sources
        ]
        if briefing is not None:
            answer = briefing
            reasoning = briefing.reasoning
        else:
            answer = Briefing(
                current_situation=NOT_COVERED_SENTENCE,
                key_developments=[],
                key_actors=[],
                reasoning="",
            )
            reasoning = ""
        return AnswerReport(
            covered=covered,
            answer=answer,
            reasoning=reasoning,
            documents_used=[doc.id for doc in documents],
            evidence=evidence,
            sources=sources,
            retrieval=diagnostics,
            ranking=retrieval.ranking,
            provider=self._config.provider,
            model=self._config.model,
            generated_at=self._clock().isoformat(),
        )
