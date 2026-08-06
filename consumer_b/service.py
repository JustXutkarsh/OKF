"""ConsumerService: the sole orchestration layer and public interface.

Flow: question → scan catalog → retrieve → NOT_COVERED short-circuit →
read selected documents (only) → LLM → validate JSON → verify conflicts
verbatim against retrieved docs → Python builds Sources/Evidence →
AnswerReport.

analyze() returns an AnswerReport object, never formatted text: the CLI
renders for the console; a future backend API serializes the same object.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from consumer_b import NOT_COVERED_SENTENCE, prompts
from consumer_b.exceptions import RetrievalError
from consumer_b.llm import ChatClient, parse_analysis
from consumer_b.models import (
    AnswerReport,
    BundleDocument,
    ConsumerConfig,
    CriticalAnalysis,
    CriticalAnalysisReport,
    EvidenceEntry,
    ReportSource,
    RetrievalDiagnostics,
    RetrievalResult,
)
from consumer_b.observability import StageTimer, log_event
from consumer_b.reader import read_documents, scan_catalog
from consumer_b.retriever import select
from consumer_b.verifier import verify_conflicts

BRIEFING_SECTIONS = ("Summary", "Developments", "Key Actors")


class ConsumerService:
    """Orchestrates critical analysis. Public interface: analyze()."""

    def __init__(
        self,
        config: ConsumerConfig,
        llm_client: Any = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._llm_client = llm_client
        self._clock = clock or (lambda: datetime.now(UTC))

    def analyze(self, question: str, max_docs: int | None = None) -> AnswerReport:
        """Produce a critical analysis strictly from the bundle."""

        if not question or not question.strip():
            raise RetrievalError("Question must not be empty.")

        config = self._config
        limit = max_docs or config.max_docs
        question_hash = hashlib.sha1(question.encode("utf-8")).hexdigest()[:10]
        log_event("analyze.start", question_hash=question_hash, question_len=len(question))

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
                    "analyze.complete",
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
            analysis = parse_analysis(raw)
            log_event("stage", stage="llm", duration_ms=stage.duration_ms)

            covered = not _is_not_covered(analysis)
            verified: list = []
            discarded: list[str] = []
            if covered:
                with StageTimer() as stage:
                    verified, discarded = verify_conflicts(analysis.conflicting_evidence, documents)
                log_event(
                    "stage",
                    stage="verify",
                    duration_ms=stage.duration_ms,
                    verified_conflicts=len(verified),
                    discarded_conflicts=len(discarded),
                )
                for reason in discarded:
                    log_event("conflict.discarded", reason=reason)

            report = self._build_report(
                analysis if covered else None,
                documents,
                retrieval,
                diagnostics,
                verified_conflicts=verified,
            )
            log_event(
                "analyze.complete",
                question_hash=question_hash,
                outcome="covered" if covered else "not-covered",
                total_ms=total.elapsed_ms(),
            )
            return report

    def _build_report(
        self,
        analysis: CriticalAnalysis | None,
        documents: list[BundleDocument],
        retrieval: RetrievalResult,
        diagnostics: RetrievalDiagnostics,
        verified_conflicts: list | None = None,
    ) -> AnswerReport:
        """Python-only assembly of verified conflicts, sources, evidence."""

        covered = analysis is not None
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
        if analysis is not None:
            report_analysis = CriticalAnalysisReport(
                assumptions=analysis.assumptions,
                conflicting_evidence=verified_conflicts or [],
                uncertainties=analysis.uncertainties,
                alternative_interpretations=analysis.alternative_interpretations,
                missing_information=analysis.missing_information,
                confidence_assessment=analysis.confidence_assessment,
            )
            reasoning = analysis.reasoning
        else:
            report_analysis = CriticalAnalysisReport(confidence_assessment=NOT_COVERED_SENTENCE)
            reasoning = ""
        return AnswerReport(
            covered=covered,
            critical_analysis=report_analysis,
            reasoning=reasoning,
            documents_used=[doc.id for doc in documents],
            evidence=evidence,
            sources=sources,
            retrieval=diagnostics,
            ranking=retrieval.ranking,
            provider=self._config.provider,
            model=self._config.model,
            generated_at=self._clock().isoformat(),
            bundle_version=_bundle_version(retrieval),
        )


def _is_not_covered(analysis: CriticalAnalysis) -> bool:
    """LLM-declared uncovered: all lists empty, sentence in confidence field."""

    return (
        not analysis.assumptions
        and not analysis.conflicting_evidence
        and not analysis.uncertainties
        and not analysis.alternative_interpretations
        and not analysis.missing_information
        and analysis.confidence_assessment.strip() == NOT_COVERED_SENTENCE
    )


def _bundle_version(retrieval: RetrievalResult) -> int | str | None:
    """Propagate schema_version only when all retrieved documents agree."""

    versions = {entry.schema_version for entry in retrieval.selected}
    if len(versions) == 1:
        return versions.pop()
    if len(versions) > 1:
        logging.getLogger("consumer_b").warning(
            "bundle_version is null: retrieved documents disagree on schema_version %s",
            sorted(versions, key=str),
        )
    return None
