"""Custom exceptions for producer control flow."""

from __future__ import annotations

from validator.models import ValidationResult


class ProducerError(Exception):
    """Base class for all producer failures."""


class ConfigError(ProducerError):
    """Raised for invalid configuration, including missing API keys."""


class RegistryError(ConfigError):
    """Raised when the tracked-concept registry is invalid or incomplete."""


class SearchError(ProducerError):
    """Raised when search fails or returns a malformed response."""


class LLMResponseError(ProducerError):
    """Raised when the LLM call fails or returns unusable output."""


class DocumentParseError(ProducerError):
    """Raised when an existing bundle document cannot be parsed safely."""


class ValidationFailure(ProducerError):
    """Raised when the staged bundle fails validation; nothing is written."""

    def __init__(self, result: ValidationResult, staged_bundle: str | None = None) -> None:
        codes = ", ".join(sorted({error.code for error in result.errors}))
        message = f"Staged bundle failed validation: {codes}"
        if staged_bundle:
            message += f" (staged bundle kept at: {staged_bundle})"
        super().__init__(message)
        self.result = result
        self.staged_bundle = staged_bundle
        self.validation_errors = [
            {
                "code": error.code,
                "file": error.file,
                "line": error.line,
                "message": error.rule,
                "suggestion": error.suggested_fix,
            }
            for error in result.errors
        ]
