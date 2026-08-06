"""Pure rendering: AnswerReport → console text or the stable JSON contract.

This module never calls the LLM, never touches files, never retrieves,
and never computes evidence or sources — it converts a finished
AnswerReport into presentation, nothing else.
"""

from __future__ import annotations

import json

from consumer_a import NOT_COVERED_SENTENCE
from consumer_a.models import AnswerReport


def render_text(report: AnswerReport) -> str:
    """Human-readable briefing. Uncovered questions print the sentence only."""

    if not report.covered:
        return NOT_COVERED_SENTENCE

    lines: list[str] = ["## Current Situation", "", report.answer.current_situation, ""]

    if report.answer.key_developments:
        lines.append("## Key Developments")
        lines.append("")
        lines.extend(f"- {item}" for item in report.answer.key_developments)
        lines.append("")

    if report.answer.key_actors:
        lines.append("## Key Actors")
        lines.append("")
        lines.extend(f"- {item}" for item in report.answer.key_actors)
        lines.append("")

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


def render_json(report: AnswerReport) -> str:
    """The stable JSON contract — the future backend API response shape."""

    payload = {
        "answer": {
            "current_situation": report.answer.current_situation,
            "key_developments": report.answer.key_developments,
            "key_actors": report.answer.key_actors,
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
    }
    return json.dumps(payload, indent=2)
