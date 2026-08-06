"""Custom exceptions for Consumer B control flow (independent hierarchy)."""


class ConsumerError(Exception):
    """Base class for all Consumer B failures."""


class ConfigError(ConsumerError):
    """Raised for invalid configuration, keys, or bundle path."""


class DocumentReadError(ConsumerError):
    """Raised when a bundle document is malformed (bad YAML, bad structure)."""


class FilesystemError(ConsumerError):
    """Raised when a bundle document cannot be read from disk."""


class RetrievalError(ConsumerError):
    """Raised when a question cannot be processed for retrieval."""


class LLMResponseError(ConsumerError):
    """Raised when the LLM call fails or returns unusable output."""


class TimeoutError(ConsumerError):
    """Raised when the LLM provider does not answer in time."""
