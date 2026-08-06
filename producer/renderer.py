"""Pure serialization of the Document model into canonical markdown text.

No business logic, no validation, no timestamps, no source merging:
this module renders exactly what the Document model contains, in the
canonical layout the validator and the seed bundle expect.
"""

from __future__ import annotations

import re

from producer.models import Document

# Plain (unquoted) YAML scalars: commas are legal in block context but are
# separators in flow context, so flow-list items use the stricter pattern.
_PLAIN_SCALAR = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._\-/()'&,]*")
_PLAIN_FLOW_ITEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._\-/()'&]*")


def render_document(document: Document) -> str:
    """Serialize one Document into canonical markdown text."""

    lines: list[str] = ["---"]
    lines.extend(_frontmatter_lines(document))
    lines.append("---")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(document.summary.strip())
    lines.append("")

    lines.append("## Developments")
    for entry in document.developments:
        lines.append("")
        lines.append(f"### {entry.date}")
        lines.append("")
        lines.append(entry.text.strip())
    lines.append("")

    lines.append("## Key Actors")
    lines.append("")
    lines.extend(f"- {actor}" for actor in document.key_actors)
    lines.append("")

    lines.append("## Sources")
    lines.append("")
    for source in document.sources:
        lines.append(f"- title: {_yaml_scalar(source.title)}")
        lines.append(f"  url: {source.url}")
        lines.append(f"  accessed: {source.accessed}")
        lines.append(f"  note: {_yaml_scalar(source.note)}")

    return "\n".join(lines) + "\n"


def _frontmatter_lines(document: Document) -> list[str]:
    """Render frontmatter in the fixed canonical field order."""

    return [
        f"schema_version: {document.schema_version}",
        f"id: {_yaml_scalar(document.id)}",
        f"type: {_yaml_scalar(document.type)}",
        f"title: {_yaml_scalar(document.title)}",
        f"resource: {_yaml_scalar(document.resource)}",
        f"tags: {_yaml_flow_list(document.tags)}",
        f"created_at: {document.created_at}",
        f"last_updated: {document.last_updated}",
        f"confidence: {_yaml_scalar(document.confidence)}",
        f"related: {_yaml_flow_list(document.related)}",
    ]


def _yaml_flow_list(values: list[str]) -> str:
    return "[" + ", ".join(_yaml_scalar(value, _PLAIN_FLOW_ITEM) for value in values) + "]"


def _yaml_scalar(value: object, plain_pattern: re.Pattern[str] = _PLAIN_SCALAR) -> str:
    """Render a YAML scalar, quoting only when plain style would be unsafe."""

    text = str(value)
    if text and plain_pattern.fullmatch(text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
