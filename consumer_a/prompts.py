"""All Consumer A prompts, isolated in one module.

The LLM receives ONLY the user question and the selected document text
(title, summary, developments, key actors). It never sees URLs, sources,
file paths, document ids, frontmatter, or generated timestamps — nothing
but what reasoning requires. It returns JSON only; Python validates the
schema and owns everything else (sources, evidence, rendering).
"""

from __future__ import annotations

from consumer_a import NOT_COVERED_SENTENCE
from consumer_a.models import BundleDocument

SYSTEM_PROMPT = (
    "You are a geopolitical briefing agent. You answer questions using ONLY the "
    "documents provided in the user message.\n\n"
    "Respond with a single JSON object and nothing else:\n"
    '{"current_situation": "...", "key_developments": ["..."], '
    '"key_actors": ["..."], "reasoning": "..."}\n\n'
    "Hard rules:\n"
    "- Use ONLY the provided documents. NEVER use outside or background knowledge.\n"
    "- NEVER invent facts, actors, sources, citations, or URLs.\n"
    "- NEVER infer information that is missing from the documents.\n"
    "- key_actors: only actors explicitly named in the documents.\n"
    "- key_developments: short bullets, newest information first.\n"
    "- reasoning: 1-2 sentences on how the documents support the answer.\n"
    "- No markdown, no headings, no code fences, no YAML, no links in any value.\n"
    "- If the documents conflict, state the conflict explicitly in "
    "current_situation.\n"
    '- If the documents cannot answer the question, respond with exactly: '
    '{"current_situation": "' + NOT_COVERED_SENTENCE + '", '
    '"key_developments": [], "key_actors": [], "reasoning": ""}'
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
