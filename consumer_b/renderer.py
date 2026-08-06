"""Pure rendering: AnswerReport → console text or the stable JSON contract.

Never calls the LLM, never touches files, never retrieves, never verifies,
never computes evidence/sources, never logs. Presentation only.
"""

from __future__ import annotations

import json

from consumer_b import NOT_COVERED_SENTENCE


def render_text(report) -> str:
    """Human-readable critical analysis. Uncovered prints the sentence only."""

    if not report.covered:
        return NOT_COVERED_SENTENCE

    analysis = report.critical_analysis
    lines: list[str] = []

    def section(title: str, items: list[str]) -> None:
        if items:
            lines.append(f"## {title}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")

    if analysis.confidence_assessment:
        lines.extend(["## Confidence Assessment", "", analysis.confidence_assessment, ""])
    section("Assumptions", analysis.assumptions)
    if analysis.conflicting_evidence:
        lines.append("## Conflicting Evidence")
        lines.append("")
        for conflict in analysis.conflicting_evidence:
            lines.append(f"- {conflict.description}")
            lines.append(f"  Documents: {', '.join(conflict.document_ids)}")
            lines.append(f'  Supporting: "{conflict.supporting_text}"')
            lines.append(f'  Conflicting: "{conflict.conflicting_text}"')
        lines.append("")
    section("Uncertainties", analysis.uncertainties)
    section("Alternative Interpretations", analysis.alternative_interpretations)
    section("Missing Information", analysis.missing_information)

    if report.evidence:
        lines.append("## Evidence")
        lines.append("")
        lines.extend(
            f"- {item.document_id} — {item.section} "
            f"(score {item.matching_score}, confidence: {item.confidence})"
            for item in report.evidence
        )
        lines.append("")

    if report.sources:
        lines.append("## Sources")
        lines.append("")
        lines.extend(
            f"- {item.document_id} ({item.document_title}): {item.source_title} — "
            f"{item.source_url} (accessed {item.accessed_date})"
            for item in report.sources
        )

    return "\n".join(lines).rstrip()


def render_json(report) -> str:
    """The stable JSON contract — the future backend API response shape."""

    payload = {
        "critical_analysis": {
            "assumptions": report.critical_analysis.assumptions,
            "conflicting_evidence": [
                item.model_dump() for item in report.critical_analysis.conflicting_evidence
            ],
            "uncertainties": report.critical_analysis.uncertainties,
            "alternative_interpretations": report.critical_analysis.alternative_interpretations,
            "missing_information": report.critical_analysis.missing_information,
            "confidence_assessment": report.critical_analysis.confidence_assessment,
        },
        "reasoning": report.reasoning,
        "documents_used": report.documents_used,
        "evidence": [item.model_dump() for item in report.evidence],
        "sources": [item.model_dump() for item in report.sources],
        "retrieval": report.retrieval.model_dump(),
        "ranking": [item.model_dump() for item in report.ranking],
        "generated_at": report.generated_at,
        "provider": report.provider,
        "model": report.model,
        "bundle_version": report.bundle_version,
    }
    return json.dumps(payload, indent=2)
