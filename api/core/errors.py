"""Uniform error envelope and exception → HTTP mapping.

Every error response has exactly one shape, and every mapped category has
exactly one status code. Stack traces never reach clients.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.models.errors import ErrorBody, ErrorEnvelope


class APIError(Exception):
    """Deliberate API-layer failure with a stable code and status.

    ``details`` carries optional structured diagnostics (e.g. the full
    validation-error list for bundle validation failures) that surfaces in
    job records — never in the client-facing HTTP error envelope, whose
    shape stays frozen.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def envelope(status: int, code: str, message: str, request_id: str) -> JSONResponse:
    body = ErrorEnvelope(error=ErrorBody(code=code, message=message, request_id=request_id))
    return JSONResponse(status_code=status, content=body.model_dump())


def map_component_error(exc: Exception) -> APIError:
    """Map a producer/consumer-domain exception onto the API taxonomy."""

    from consumer_a.exceptions import ConfigError as AConfigError
    from consumer_a.exceptions import DocumentReadError as ADocError
    from consumer_a.exceptions import FilesystemError as AFilesystemError
    from consumer_a.exceptions import LLMResponseError as ALLMError
    from consumer_a.exceptions import RetrievalError as ARetrievalError
    from consumer_a.exceptions import TimeoutError as ATimeoutError
    from consumer_b.exceptions import ConfigError as BConfigError
    from consumer_b.exceptions import DocumentReadError as BDocError
    from consumer_b.exceptions import FilesystemError as BFilesystemError
    from consumer_b.exceptions import LLMResponseError as BLLMError
    from consumer_b.exceptions import RetrievalError as BRetrievalError
    from consumer_b.exceptions import TimeoutError as BTimeoutError
    from producer.exceptions import ConfigError as PConfigError
    from producer.exceptions import LLMResponseError as PLLMError
    from producer.exceptions import RegistryError, SearchError, ValidationFailure

    if isinstance(exc, ValidationFailure):
        details: dict[str, object] = {"validation_errors": exc.validation_errors}
        if exc.staged_bundle:
            details["staged_bundle"] = exc.staged_bundle
        return APIError(409, "BUNDLE_VALIDATION_FAILED", str(exc), details=details)
    if isinstance(exc, (ARetrievalError, BRetrievalError)):
        return APIError(422, "INVALID_REQUEST", str(exc))
    if isinstance(exc, (ATimeoutError, BTimeoutError)):
        return APIError(504, "UPSTREAM_TIMEOUT", str(exc))
    if isinstance(exc, (ALLMError, BLLMError, PLLMError)):
        return APIError(502, "UPSTREAM_LLM", str(exc))
    if isinstance(exc, SearchError):
        return APIError(502, "UPSTREAM_SEARCH", str(exc))
    if isinstance(exc, (ADocError, BDocError, AFilesystemError, BFilesystemError)):
        return APIError(503, "BUNDLE_UNAVAILABLE", str(exc))
    if isinstance(exc, (AConfigError, BConfigError, PConfigError, RegistryError)):
        return APIError(503, "MISCONFIGURED", str(exc))
    return APIError(500, "INTERNAL", "Unexpected internal error.")


def register_exception_handlers(app: FastAPI) -> None:
    """Install the deterministic handlers on the app."""

    from consumer_a.exceptions import ConsumerError as ConsumerAError
    from consumer_b.exceptions import ConsumerError as ConsumerBError
    from producer.exceptions import ProducerError

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        return envelope(exc.status, exc.code, exc.message, request.state.request_id)

    async def component_handler(request: Request, exc: Exception) -> JSONResponse:
        mapped = map_component_error(exc)
        return envelope(mapped.status, mapped.code, mapped.message, request.state.request_id)

    # Any exception from the three independent component hierarchies maps
    # onto the documented taxonomy (502/503/504/409/422) via the base classes.
    for base in (ConsumerAError, ConsumerBError, ProducerError):
        app.add_exception_handler(base, component_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return envelope(
            422, "INVALID_REQUEST", "Request validation failed.", request.state.request_id
        )

    @app.exception_handler(Exception)
    async def fallback_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger("api").debug("unhandled error", exc_info=exc)
        return envelope(500, "INTERNAL", "Unexpected internal error.", request.state.request_id)
