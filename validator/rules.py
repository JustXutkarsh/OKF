"""Independent deterministic validation rules for OKF documents."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from validator.models import ParsedDocument, ValidationError

REQUIRED_FIELDS = (
    "schema_version",
    "id",
    "type",
    "title",
    "resource",
    "created_at",
    "last_updated",
    "tags",
    "related",
    "confidence",
)
REQUIRED_SECTIONS = ("Summary", "Developments", "Key Actors", "Sources")
LIST_FIELDS = ("tags", "related")
DATE_FIELDS = ("created_at", "last_updated")
SOURCE_REQUIRED_FIELDS = ("title", "url", "accessed", "note")


def validate_documents(documents: list[ParsedDocument], root: Path) -> list[ValidationError]:
    """Run every rule and return all validation errors."""

    errors: list[ValidationError] = []
    for rule in _per_document_rules():
        for document in documents:
            errors.extend(rule(document, root))

    errors.extend(validate_unique_ids(documents))
    errors.extend(validate_related_ids(documents))
    return sorted(errors, key=lambda err: (err.file, err.line or 0, err.code))


def validate_required_fields(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure every required YAML field exists."""

    del root
    errors: list[ValidationError] = []
    for field in REQUIRED_FIELDS:
        if field not in document.frontmatter:
            errors.append(
                _error(
                    "OKF003",
                    document,
                    None,
                    "Missing required field",
                    f"Add `{field}` to the YAML frontmatter.",
                    field,
                )
            )
    return errors


def validate_empty_required_fields(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure present required YAML fields are not empty."""

    del root
    errors: list[ValidationError] = []
    for field in REQUIRED_FIELDS:
        if field in document.frontmatter and _is_empty(document.frontmatter[field]):
            errors.append(
                _error(
                    "OKF004",
                    document,
                    document.field_lines.get(field),
                    "Empty required field",
                    f"Set `{field}` to a non-empty value.",
                    field,
                )
            )
    return errors


def validate_field_types(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure list fields have deterministic YAML list values."""

    del root
    errors: list[ValidationError] = []
    for field in LIST_FIELDS:
        value = document.frontmatter.get(field)
        if value is not None and not isinstance(value, list):
            errors.append(
                _error(
                    "OKF005",
                    document,
                    document.field_lines.get(field),
                    "Invalid field type",
                    f"Set `{field}` to a YAML list.",
                    field,
                )
            )
    return errors


def validate_filename_matches_id(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure the markdown filename matches the document id."""

    del root
    doc_id = document.frontmatter.get("id")
    if not isinstance(doc_id, str) or not doc_id:
        return []

    expected = f"{doc_id}.md"
    actual = Path(document.relative_path).name
    if actual == expected:
        return []
    return [
        _error(
            "OKF008",
            document,
            document.field_lines.get("id"),
            "Filename does not match document id",
            f"Rename the file to `{expected}` or update `id` to match the filename.",
            "id",
        )
    ]


def validate_folder_matches_resource(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure the parent folder under okf matches the resource field."""

    del root
    resource = document.frontmatter.get("resource")
    if not isinstance(resource, str) or not resource:
        return []

    parts = Path(document.relative_path).parts
    actual = parts[0] if len(parts) > 1 else ""
    if actual == resource:
        return []
    return [
        _error(
            "OKF009",
            document,
            document.field_lines.get("resource"),
            "Folder does not match resource",
            f"Move the file under `{resource}/` or update `resource` to `{actual}`.",
            "resource",
        )
    ]


def validate_required_sections(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure all required markdown sections are present."""

    del root
    errors: list[ValidationError] = []
    for section in REQUIRED_SECTIONS:
        if section not in document.section_lines:
            errors.append(
                _error(
                    "OKF010",
                    document,
                    None,
                    "Missing required markdown section",
                    f"Add `## {section}` to the document body.",
                )
            )
    return errors


def validate_sources_format(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure Sources contains structured source entries."""

    del root
    if "Sources" not in document.section_lines:
        return []

    source_lines = _section_content_lines(document, "Sources")
    non_empty = [(line_no, text) for line_no, text in source_lines if text.strip()]
    if not non_empty:
        return [
            _error(
                "OKF011",
                document,
                document.section_lines["Sources"],
                "Empty Sources section",
                "Add at least one structured source with title, url, accessed, and note.",
            )
        ]

    errors: list[ValidationError] = []
    entries = _source_entries(non_empty)
    for entry in entries:
        fields = entry["fields"]
        if not fields:
            errors.append(
                _error(
                    "OKF011",
                    document,
                    entry["line"],
                    "Invalid source format",
                    "Use `- title:` followed by indented url, accessed, and note fields.",
                )
            )
            continue

        for field in SOURCE_REQUIRED_FIELDS:
            value = fields.get(field)
            if not value:
                errors.append(
                    _error(
                        "OKF011",
                        document,
                        entry["line"],
                        "Invalid source format",
                        f"Add non-empty `{field}` to this source entry.",
                    )
                )
        url = fields.get("url", "")
        if url and not re.match(r"^https?://\S+$", url):
            errors.append(
                _error(
                    "OKF011",
                    document,
                    entry["line"],
                    "Invalid source URL",
                    "Set `url` to an absolute http or https URL.",
                )
            )
        accessed = fields.get("accessed", "")
        if accessed and not _is_iso_date(accessed):
            errors.append(
                _error(
                    "OKF011",
                    document,
                    entry["line"],
                    "Invalid source accessed date",
                    "Set `accessed` to an ISO date in YYYY-MM-DD format.",
                )
            )
    return errors


def validate_iso_dates(document: ParsedDocument, root: Path) -> list[ValidationError]:
    """Ensure metadata and development dates use ISO YYYY-MM-DD format."""

    del root
    errors: list[ValidationError] = []
    for field in DATE_FIELDS:
        if field in document.frontmatter and not _is_iso_date(document.frontmatter[field]):
            errors.append(
                _error(
                    "OKF012",
                    document,
                    document.field_lines.get(field),
                    "Invalid ISO date",
                    f"Set `{field}` to an ISO date in YYYY-MM-DD format.",
                    field,
                )
            )

    for index, line in enumerate(document.lines, start=1):
        if line.startswith("### "):
            value = line[4:].strip()
            if not _is_iso_date(value):
                errors.append(
                    _error(
                        "OKF012",
                        document,
                        index,
                        "Invalid development date",
                        "Use `### YYYY-MM-DD` for development entries.",
                    )
                )
    return errors


def validate_unique_ids(documents: list[ParsedDocument]) -> list[ValidationError]:
    """Ensure every non-empty document id appears once."""

    ids = [
        doc.frontmatter.get("id")
        for doc in documents
        if isinstance(doc.frontmatter.get("id"), str) and doc.frontmatter.get("id")
    ]
    counts = Counter(ids)
    errors: list[ValidationError] = []
    for document in documents:
        doc_id = document.frontmatter.get("id")
        if isinstance(doc_id, str) and counts[doc_id] > 1:
            errors.append(
                _error(
                    "OKF006",
                    document,
                    document.field_lines.get("id"),
                    "Duplicate document id",
                    f"Change `id` to a unique stable ID; `{doc_id}` is used more than once.",
                    "id",
                )
            )
    return errors


def validate_related_ids(documents: list[ParsedDocument]) -> list[ValidationError]:
    """Ensure every related id exists in the bundle."""

    known_ids = {
        doc.frontmatter.get("id")
        for doc in documents
        if isinstance(doc.frontmatter.get("id"), str)
    }
    errors: list[ValidationError] = []
    for document in documents:
        related = document.frontmatter.get("related")
        if not isinstance(related, list):
            continue
        for related_id in related:
            if related_id not in known_ids:
                errors.append(
                    _error(
                        "OKF007",
                        document,
                        document.field_lines.get("related"),
                        "Related id does not exist",
                        f"Add a document with id `{related_id}` or remove it from `related`.",
                        "related",
                    )
                )
    return errors


def _per_document_rules() -> tuple[Callable[[ParsedDocument, Path], list[ValidationError]], ...]:
    """Return per-document rules in deterministic order."""

    return (
        validate_required_fields,
        validate_empty_required_fields,
        validate_field_types,
        validate_filename_matches_id,
        validate_folder_matches_resource,
        validate_required_sections,
        validate_sources_format,
        validate_iso_dates,
    )


def _section_content_lines(document: ParsedDocument, section: str) -> list[tuple[int, str]]:
    """Return body lines belonging to one H2 section."""

    start = document.section_lines[section] + 1
    next_headers = [
        line_no for name, line_no in document.section_lines.items() if line_no > start and name != section
    ]
    end = min(next_headers) if next_headers else len(document.lines) + 1
    return [(line_no, document.lines[line_no - 1]) for line_no in range(start, end)]


def _source_entries(lines: list[tuple[int, str]]) -> list[dict[str, Any]]:
    """Parse structured source entries from non-empty Sources lines."""

    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line_no, text in lines:
        stripped = text.strip()
        if stripped.startswith("- title:"):
            current = {"line": line_no, "fields": {"title": stripped.removeprefix("- title:").strip()}}
            entries.append(current)
            continue
        if current is None or not text.startswith("  "):
            entries.append({"line": line_no, "fields": {}})
            current = None
            continue
        key, separator, value = stripped.partition(":")
        if not separator:
            current["fields"][""] = ""
            continue
        current["fields"][key] = value.strip()
    return entries


def _is_empty(value: Any) -> bool:
    """Return True when a required field value is empty."""

    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _is_iso_date(value: Any) -> bool:
    """Return True when value represents exactly YYYY-MM-DD."""

    if isinstance(value, date) and not isinstance(value, datetime):
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def _error(
    code: str,
    document: ParsedDocument,
    line: int | None,
    rule: str,
    suggested_fix: str,
    field: str | None = None,
) -> ValidationError:
    """Create a validation error for one document."""

    return ValidationError(
        code=code,
        file=document.relative_path,
        line=line,
        rule=rule,
        field=field,
        suggested_fix=suggested_fix,
    )
