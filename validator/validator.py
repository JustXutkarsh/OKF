"""Bundle-level validator orchestration."""

from __future__ import annotations

from pathlib import Path

from validator.models import ParsedDocument, ValidationResult
from validator.parser import parse_document
from validator.rules import validate_documents


def validate_bundle(bundle_path: str | Path) -> ValidationResult:
    """Validate every markdown document below an OKF bundle path."""

    root = Path(bundle_path).resolve()
    documents: list[ParsedDocument] = []
    errors = []

    for path in sorted(root.rglob("*.md")):
        result = parse_document(path, root)
        errors.extend(result.errors)
        if result.document is not None:
            documents.append(result.document)

    errors.extend(validate_documents(documents, root))
    errors = sorted(errors, key=lambda err: (err.file, err.line or 0, err.code))
    return ValidationResult(checked=len(documents), errors=errors)
