"""Development entrypoint: python -m api (production uses uvicorn directly)."""

from __future__ import annotations

from api.core.config import load_settings
from api.main import create_app


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
