"""Pydantic models used by the OKF validator."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidationError(BaseModel):
    """A deterministic validation error with a stable error code."""

    code: str
    file: str
    line: int | None = None
    rule: str
    field: str | None = None
    suggested_fix: str


class ParsedDocument(BaseModel):
    """A markdown document parsed into frontmatter, body, and line metadata."""

    file_path: str
    relative_path: str
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    body: str = ""
    lines: list[str] = Field(default_factory=list)
    field_lines: dict[str, int] = Field(default_factory=dict)
    section_lines: dict[str, int] = Field(default_factory=dict)


class ParseResult(BaseModel):
    """Result of parsing one markdown document."""

    document: ParsedDocument | None = None
    errors: list[ValidationError] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of validating a bundle."""

    checked: int
    errors: list[ValidationError] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when the bundle has no validation errors."""

        return not self.errors
