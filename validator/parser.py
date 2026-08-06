"""Markdown and YAML frontmatter parsing for OKF documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from validator.models import ParsedDocument, ParseResult, ValidationError

FIELD_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$")


def parse_document(path: Path, root: Path) -> ParseResult:
    """Parse one markdown document and return all parse-level errors."""

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    relative_path = path.relative_to(root).as_posix()

    if not lines or lines[0].strip() != "---":
        return ParseResult(
            errors=[
                ValidationError(
                    code="OKF001",
                    file=relative_path,
                    line=1,
                    rule="Missing YAML frontmatter",
                    suggested_fix="Start the document with a YAML frontmatter block delimited by ---.",
                )
            ]
        )

    end_index = _find_frontmatter_end(lines)
    if end_index is None:
        return ParseResult(
            errors=[
                ValidationError(
                    code="OKF001",
                    file=relative_path,
                    line=1,
                    rule="Unclosed YAML frontmatter",
                    suggested_fix="Add a closing --- line after the YAML frontmatter.",
                )
            ]
        )

    yaml_lines = lines[1:end_index]
    body_lines = lines[end_index + 1 :]
    errors: list[ValidationError] = []
    frontmatter: dict[str, Any] = {}

    try:
        loaded = yaml.safe_load("\n".join(yaml_lines)) or {}
        if isinstance(loaded, dict):
            frontmatter = loaded
        else:
            errors.append(
                ValidationError(
                    code="OKF002",
                    file=relative_path,
                    line=2,
                    rule="Invalid YAML frontmatter",
                    suggested_fix="Use a YAML mapping of field names to values.",
                )
            )
    except yaml.YAMLError as exc:
        errors.append(_yaml_error(relative_path, exc))

    document = ParsedDocument(
        file_path=str(path),
        relative_path=relative_path,
        frontmatter=frontmatter,
        body="\n".join(body_lines),
        lines=lines,
        field_lines=_field_lines(yaml_lines),
        section_lines=_section_lines(body_lines, end_index + 2),
    )
    return ParseResult(document=document, errors=errors)


def _find_frontmatter_end(lines: list[str]) -> int | None:
    """Return the zero-based line index of the closing frontmatter delimiter."""

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index
    return None


def _field_lines(yaml_lines: list[str]) -> dict[str, int]:
    """Map top-level YAML field names to one-based source line numbers."""

    result: dict[str, int] = {}
    for index, line in enumerate(yaml_lines, start=2):
        match = FIELD_PATTERN.match(line)
        if match:
            result[match.group(1)] = index
    return result


def _section_lines(body_lines: list[str], first_line_number: int) -> dict[str, int]:
    """Map markdown H2 section names to one-based source line numbers."""

    result: dict[str, int] = {}
    for offset, line in enumerate(body_lines):
        match = SECTION_PATTERN.match(line)
        if match:
            result[match.group(1)] = first_line_number + offset
    return result


def _yaml_error(file: str, exc: yaml.YAMLError) -> ValidationError:
    """Convert a PyYAML exception into a stable validation error."""

    line = None
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        line = 2 + int(mark.line)
    return ValidationError(
        code="OKF002",
        file=file,
        line=line,
        rule="Invalid YAML syntax",
        suggested_fix="Fix the YAML frontmatter syntax.",
    )
