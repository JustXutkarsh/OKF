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

    def __init__(self, result: ValidationResult) -> None:
        codes = ", ".join(sorted({error.code for error in result.errors}))
        super().__init__(f"Staged bundle failed validation: {codes}")
        self.result = result
