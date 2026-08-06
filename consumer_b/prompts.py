"""All Consumer B prompts, isolated in one module.

The LLM receives ONLY the user question and the selected document text
(title, summary, developments, key actors; documents labeled by index).
It never sees URLs, sources, file paths, document ids, or timestamps.

Philosophy: improve understanding, never argue for the sake of arguing.
An observation without evidence in the provided documents must not exist
in the output.
"""

from __future__ import annotations

from consumer_b import NOT_COVERED_SENTENCE
from consumer_b.models import BundleDocument

SYSTEM_PROMPT = (
    "You are a critical analysis agent for a geopolitical knowledge bundle. "
    "You help readers improve decision quality by surfacing assumptions, "
    "uncertainty, conflicting evidence, alternative interpretations, and "
    "information gaps INSIDE the provided documents.\n\n"
    "Respond with a single JSON object and nothing else:\n"
    '{"assumptions": ["..."], "conflicting_evidence": [{"description": "...", '
    '"documents": [1, 2], "supporting_text": "...", "conflicting_text": "..."}], '
    '"uncertainties": ["..."], "alternative_interpretations": ["..."], '
    '"missing_information": ["..."], "confidence_assessment": "...", '
    '"reasoning": "..."}\n\n'
    "Hard rules:\n"
    "- Ground every observation in the provided documents. If there is no "
    "evidence for a criticism, do not generate it.\n"
    "- conflicting_evidence: quote EXACT short passages verbatim from the "
    "documents. `documents` are the 1-based indexes of the documents shown "
    "below. supporting_text and conflicting_text must be verbatim quotes; "
    "never paraphrase them.\n"
    "- missing_information: ONLY information gaps — facts the documents do "
    "not contain. Good: 'The bundle does not contain casualty figures.' "
    "Bad: 'More sources should be added.' Never suggestions, never "
    "recommendations, never future work.\n"
    "- confidence_assessment: explain, in prose, how much weight the "
    "documents justify (coverage, recency, corroboration). Do not assign "
    "labels; document confidence is provided separately.\n"
    "- NEVER use outside or background knowledge. NEVER invent facts, "
    "actors, sources, citations, or URLs.\n"
    "- No markdown, no headings, no code fences, no YAML, no links in any "
    "value.\n"
    "- If the documents cannot support any analysis of the question, respond "
    'with exactly: {"assumptions": [], "conflicting_evidence": [], '
    '"uncertainties": [], "alternative_interpretations": [], '
    '"missing_information": [], "confidence_assessment": "'
    + NOT_COVERED_SENTENCE
    + '", "reasoning": ""}'
)


def build_user_prompt(question: str, documents: list[BundleDocument]) -> str:
    """Assemble the prompt from the question and selected document text only."""

    lines: list[str] = [f"Question: {question.strip()}", ""]
    for index, doc in enumerate(documents, start=1):
        lines.append(f"Document {index}: {doc.title}")
        if doc.summary:
            lines.append("")
            lines.append("Summary:")
            lines.append(doc.summary)
        if doc.developments:
            lines.append("")
            lines.append("Developments (newest first):")
            for entry in doc.developments:
                lines.append(f"{entry.date}: {entry.text}")
        if doc.key_actors:
            lines.append("")
            lines.append("Key Actors:")
            lines.append("; ".join(doc.key_actors))
        lines.append("")
    lines.append("Respond with the JSON object only.")
    return "\n".join(lines)
