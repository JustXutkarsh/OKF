# syntax=docker/dockerfile:1
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependency layer cached independently from source changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root runtime user
RUN useradd --uid 10001 --create-home okf && chown -R okf:okf /app
USER okf

# Build provenance (mandate: env-driven, no runtime git inspection)
ARG OKF_API_GIT_SHA=unknown
ARG OKF_API_BUILD_TIME=unknown
ENV OKF_API_GIT_SHA=${OKF_API_GIT_SHA} \
    OKF_API_BUILD_TIME=${OKF_API_BUILD_TIME} \
    OKF_API_HOST=0.0.0.0 \
    OKF_API_PORT=8000 \
    OKF_BUNDLE_PATH=/app/okf \
    OKF_REGISTRY_PATH=/app/config/tracked_concepts.yaml

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/ready', timeout=4).status == 200 else 1)" || exit 1

# Graceful shutdown via uvicorn's SIGTERM handling + lifespan shutdown hooks
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
