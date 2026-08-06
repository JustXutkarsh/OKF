"""Custom exceptions for validator control flow."""


class ValidatorUsageError(Exception):
    """Raised when CLI arguments are valid syntax but invalid for validation."""
