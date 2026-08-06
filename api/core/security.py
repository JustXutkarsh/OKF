"""Bearer API-key authentication over hashed keys (constant-time compare)."""

from __future__ import annotations

import hmac

from fastapi import Request

from api.core.config import APISettings, hash_api_key
from api.core.errors import APIError


def authenticate(request: Request) -> str | None:
    """Return the caller's key-hash prefix when authorized, else raise 401.

    Settings come from app.state; plaintext keys never persist anywhere.
    """

    settings: APISettings = request.app.state.settings
    if settings.auth_disabled:
        return None

    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise APIError(401, "UNAUTHORIZED", "Missing Authorization: Bearer <api-key> header.")
    token_hash = hash_api_key(header[7:].strip())
    for known in settings.api_key_hashes:
        if hmac.compare_digest(token_hash, known):
            return token_hash[:12]
    raise APIError(401, "UNAUTHORIZED", "Invalid API key.")
