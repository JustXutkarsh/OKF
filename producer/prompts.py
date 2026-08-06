"""All LLM prompts, isolated in one module.

Prompts are pure functions of deterministic inputs. The LLM is asked only
for prose; it never sees URLs and never emits metadata, YAML, headings,
or dates. All of those are owned by Python.
"""

from __future__ import annotations

from producer.models import Evidence

SYSTEM_PROMPT = """You draft updates for a geopolitical knowledge document.

You will receive the concept title, the current summary, the most recent
logged development, and a numbered list of fresh evidence items.

Respond with a single JSON object and nothing else:
{"summary": "...", "development": "..."}

Hard rules:
- "summary": 2-3 sentences describing the CURRENT state, written to fully
  replace the previous summary.
- "development": one short paragraph reporting only what is NEW in the
  evidence. Do not restate the already-logged development. Dates may be
  mentioned in prose but must not be formatted as headings.
- Use ONLY the provided evidence. Never use outside or background knowledge.
- Never include URLs, domain names, markdown headings, or YAML.
- If a claim is not clearly supported by the evidence, mark it inline
  with [unverified] instead of stating it as fact.
- Neutral, factual tone. No speculation, no recommendations.
"""


def build_user_prompt(
    *,
    title: str,
    current_summary: str | None,
    latest_development_date: str | None,
    latest_development: str | None,
    evidence: list[Evidence],
) -> str:
    """Assemble the per-run user prompt from concept context and evidence."""

    lines: list[str] = [f"Concept: {title}", ""]

    lines.append("Current summary (to be replaced):")
    lines.append(current_summary or "(none — this is a new concept)")
    lines.append("")

    if latest_development and latest_development_date:
        lines.append(f"Most recent logged development ({latest_development_date}):")
        lines.append(latest_development)
    else:
        lines.append("Most recent logged development: (none)")
    lines.append("")

    lines.append("Evidence (most recent first):")
    for index, hit in enumerate(evidence, start=1):
        date_label = hit.published_date or "date unknown"
        lines.append(f"[{index}] {hit.title} ({date_label})")
        if hit.snippet.strip():
            lines.append(hit.snippet.strip())
    lines.append("")
    lines.append("Respond now with the JSON object only.")
    return "\n".join(lines)
