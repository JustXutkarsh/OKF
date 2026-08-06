# OKF Geopolitics Briefing Bundle

This repository starts with the M0 seed bundle for the Cross-Agent OKF Knowledge Exchange project.

The `okf/` directory is the portable knowledge layer. It is intentionally plain markdown with YAML frontmatter so it can be read by humans, reviewed in git, and consumed by independent agents without a shared database, SDK, API, vector store, or embedding model.

## Bundle Layout

```text
okf/
  actors/
  conflicts/
  economics/
  policy/
```

Each concept is one markdown file. The file path is useful for navigation, but metadata relationships use stable concept IDs.

## Required Frontmatter

```yaml
---
id: stable-concept-id
type: concept
title: Human-readable title
tags: [example, tags]
resource: category
last_updated: YYYY-MM-DD
related: [other-stable-id]
---
```

M0 requires every concept document to include an `id` field. Future validator work will resolve `related` IDs to files.

## Body Convention

Each concept document uses:

- `Summary`
- `Developments`
- `Key Actors`
- `Sources`

The `Summary` section is the current quick-read ground truth. `Developments` is append-only by date once producer automation exists in a later milestone.

## Producer Agent (M2)

The producer updates bundle documents from external sources. Pipeline: search → deterministic evidence filtering → one LLM draft call → document update → validation gate → atomic write. Validation runs before every write; invalid documents are never written, and prior `Developments` entries are never modified.

### Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Configuration

All settings are environment variables. A `.env` file in the repo root is loaded as a fallback for **local development only** — variables already set in the process environment always win, and the file is gitignored.

| Variable | Default | Purpose |
|---|---|---|
| `TAVILY_API_KEY` | — (required) | Search evidence (Tavily API) |
| `GROQ_API_KEY` | — (required for provider `groq`) | Groq key for drafting |
| `OPENAI_API_KEY` | — (required for provider `openai`) | OpenAI key for drafting |
| `OKF_BUNDLE_PATH` | `./okf` | Bundle directory |
| `OKF_REGISTRY_PATH` | `./config/tracked_concepts.yaml` | Tracked-concept registry |
| `OKF_PRODUCER_LLM_PROVIDER` | `groq` | Drafting provider: `groq` \| `openai` |
| `OKF_PRODUCER_MODEL` | provider default | Drafting model (`llama-3.3-70b-versatile` for groq, `gpt-4o` for openai) |
| `OKF_LOOKBACK_DAYS` | `7` | Default search lookback window |
| `OKF_MAX_RESULTS` | `5` | Default max search results |
| `OKF_REQUEST_TIMEOUT` | `30` | LLM request timeout (seconds) |
| `OKF_LOG_LEVEL` | `INFO` | Structured log level |

`.env.example` is the committed template for all components. It also pre-declares `OKF_CONSUMER_A_*` and `OKF_CONSUMER_B_*` (M3/M4): each consumer loads its own settings from its own codebase — Producer, Consumer A, and Consumer B share only the `okf/` bundle, never code. Consumer B deliberately defaults to a different LLM provider than Consumer A.

Tracked concepts and their deterministic metadata (title, tags, related, key actors, search query) live in `config/tracked_concepts.yaml`.

### Development workflow

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
printf 'TAVILY_API_KEY=...\nGROQ_API_KEY=...\n' > .env
.venv/bin/python -m unittest discover -s tests   # offline, no API keys needed
.venv/bin/python -m validator validate okf
.venv/bin/python -m producer update nato --dry-run
```

### Production workflow

Runs are stateless single processes configured purely by environment, so any scheduler (cron, systemd timer, CI) can invoke them unchanged. Cron example (daily 06:00):

```cron
0 6 * * * cd /opt/okf-bundle && .venv/bin/python -m producer update --all >> producer.log 2>&1
```

Exit codes, suitable for scheduler alerting:

| Code | Meaning |
|---|---|
| 0 | Success or no-op (already current / no evidence) |
| 1 | Unexpected producer error |
| 2 | CLI misuse |
| 3 | Configuration error (missing API key, invalid env var, invalid registry) |
| 4 | External provider failure (Tavily, LLM, network timeout) |
| 5 | Bundle validation failure — nothing was written |
| 6 | Filesystem failure |

### CLI usage

```bash
python -m producer update <concept-id> [--lookback-days N] [--max-results N] [--dry-run]
python -m producer update --all [--dry-run]
```

`--all` processes every registered concept, continues past individual failures, and exits with the highest-severity code. A same-day rerun is a no-op (`already current`) with zero API calls. `--dry-run` executes the full pipeline including validation but writes nothing.

Expected dry-run output:

```text
✔ Dry run — update for nato validated; nothing written.
File: actors/nato.md
Evidence: 4 retained (5 raw)
Sources added: 1
Confidence: verified
Validation: passed (5 documents checked)
```

Structured logs (concept id, per-stage and total durations, outcomes) go to stderr; human-readable reports go to stdout. Secrets are never logged.

### Troubleshooting

| Symptom | Exit | Cause / fix |
|---|---|---|
| `TAVILY_API_KEY is not set` / `GROQ_API_KEY is not set` | 3 | Export the key or add it to `.env` |
| `OKF_* must be an integer` | 3 | Fix the env var value |
| `Invalid .env line` | 3 | Fix `.env` syntax: one `KEY=VALUE` per line |
| `Unknown concept` | 3 | Add it to `config/tracked_concepts.yaml` |
| `Tavily search timed out` | 4 | Check connectivity; retry |
| `LLM request timed out` | 4 | Retry, or raise `OKF_REQUEST_TIMEOUT` |
| `LLM authentication failed` | 4 | Check the key for the active provider (`GROQ_API_KEY` / `OPENAI_API_KEY`) |
| `Malformed LLM response` | 4 | Transient model output; rerun (no retry by design) |
| Validation errors listed | 5 | Staged bundle invalid; nothing written — inspect reported files |
| `Filesystem error` | 6 | Check permissions/disk for the bundle path |

Deployment notes: the producer is stateless with no hardcoded paths — every location is overridable via environment. A future Dockerfile needs only a Python base image, `pip install -r requirements.txt`, and env vars; no code changes required.

## Backend API (M5)

FastAPI front-end composing the three components (never duplicating their logic). All endpoints live under `/api/v1/`; interactive docs at `/docs`.

### Run

```bash
pip install -r requirements.txt
export OKF_API_KEYS=my-secret-key           # required (stored hashed only)
.venv/bin/python -m api                      # uvicorn on OKF_API_HOST:OKF_API_PORT
```

### Endpoints

| Method & path | Purpose |
|---|---|
| `POST /api/v1/brief` | Consumer A briefing (frozen contract) |
| `POST /api/v1/analyze` | Consumer B critical analysis (frozen contract) |
| `POST /api/v1/compare` | A+B in parallel + deterministic comparison metadata |
| `POST /api/v1/producer/update` | Queue async concept update → `202` job id |
| `POST /api/v1/producer/update-all` | Queue async full update → `202` job id |
| `GET /api/v1/jobs` / `GET /api/v1/jobs/{id}` | Job list/detail (pending→running→succeeded/failed) |
| `GET /api/v1/health` / `ready` / `version` / `metrics` | Ops probes (health open; ready checks bundle+provider config) |

### Authentication

All POSTs require `Authorization: Bearer <key>`. Keys are configured via `OKF_API_KEYS` and stored **hashed only**; comparisons are constant-time. GET ops endpoints are open. `OKF_API_AUTH_DISABLED=true` exists for local dev only — never in production.

### Errors & limits

One envelope: `{"error": {"code", "message", "request_id"}}`. Codes: `UNAUTHORIZED`(401), `INVALID_REQUEST`(422), `RATE_LIMITED`(429), `UPSTREAM_LLM`/`UPSTREAM_SEARCH`(502), `BUNDLE_UNAVAILABLE`/`MISCONFIGURED`(503), `UPSTREAM_TIMEOUT`(504), `BUNDLE_VALIDATION_FAILED`(409), `INTERNAL`(500). Limits via `OKF_API_RATE_LIMIT` (default 60/min) and `OKF_API_PRODUCER_RATE_LIMIT` (5/min); `X-Request-ID` on every response.

### Docker

```bash
docker build --build-arg OKF_API_GIT_SHA=$(git rev-parse --short HEAD) \
             --build-arg OKF_API_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) -t okf-api .
docker run -p 8000:8000 -e OKF_API_KEYS=... -e TAVILY_API_KEY=... \
           -e GROQ_API_KEY=... -e OPENAI_API_KEY=... okf-api
# or: docker compose up --build
```

Non-root user; `HEALTHCHECK` hits `/api/v1/ready`; build provenance via build args.

## System Architecture

```text
            Producer (Python)                      Consumer A (Python)   Consumer B (Python)
            Tavily + LLM drafting                  Groq/OpenAI           OpenAI (default)
                   │  validation-gated writes             │                    │
                   ▼                                      │  read-only         │ read-only
              ┌──────────────────────────┐                │                    │
              │   okf/ bundle (git repo) │◄───────────────┴────────────────────┘
              │   the ONLY shared artifact
              └──────────────────────────┘
                   ▲ composed by public interfaces (no logic duplication)
                   │
              Backend API (FastAPI, /api/v1) ── auth (hashed keys) ── rate limits ── jobs
```

## CI Status

[![CI](https://github.com/JustXutkarsh/OKF/actions/workflows/ci.yml/badge.svg)](https://github.com/JustXutkarsh/OKF/actions/workflows/ci.yml)

Quality gates (mirror of `.github/workflows/ci.yml`): Ruff → Black `--check` → mypy → 170 unit tests → bundle validator → pip-audit → Docker build. CI installs from **pinned** `requirements.txt`/`requirements-dev.txt` (generated via pip-tools; regenerate with `pip-compile requirements.in` / `pip-compile --constraint requirements.txt requirements-dev.in`).

## Development Workflow

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pre-commit install        # hygiene + ruff --fix + black (fast; no mypy/tests)
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m validator validate okf
.venv/bin/ruff check . && .venv/bin/black --check . && .venv/bin/mypy
```

Consumer CLIs (development use): `.venv/bin/python -m consumer_a ask "<question>" [--json] [--max-docs N]` and `.venv/bin/python -m consumer_b analyze "<question>" [--json] [--max-docs N]`.

## Release Workflow

1. All changes merge to `main` only with a green CI run.
2. Update `CHANGELOG.md` (Keep a Changelog) and bump the version where it appears (`OKF_API_VERSION` default).
3. Tag semantically: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. Create the GitHub release from the tag; pre-release metadata uses `vX.Y.Z-rc.N` when needed.

## Deployment Workflow

```bash
docker build --build-arg OKF_API_GIT_SHA=$(git rev-parse --short HEAD) \
             --build-arg OKF_API_BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) -t okf-api:vX.Y.Z .
docker run -p 8000:8000 --env-file .env okf-api:vX.Y.Z
```

Production: inject real environment variables (never bake `.env` into images), run a single uvicorn worker (in-memory jobs/metrics/limiter by design), and place TLS termination in front. Readiness (`/api/v1/ready`) gates load balancers; `/api/v1/metrics` feeds Prometheus. See the API section above for authentication and the full environment-variable table.
