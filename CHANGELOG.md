# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-06

First production release.

### Added

- **OKF bundle (M0):** 5 hand-authored geopolitics concept documents with schema v1 frontmatter, dated Developments, and structured Sources.
- **Validator (M1):** deterministic bundle validation (12 rules, OKF001–OKF012), human/JSON CLI output.
- **Producer (M2):** validation-gated, atomic bundle updates from Tavily evidence; provider-configurable LLM drafting (groq, openai); structured logging; exit-code taxonomy; `update --all` and `--dry-run`; environment-driven config with `.env` dev fallback.
- **Consumer A (M3):** read-only briefing agent with deterministic frontmatter-catalog retrieval, LLM constrained to reasoning JSON, Python-built evidence/sources, and a stable JSON contract.
- **Consumer B (M4):** read-only critical-analysis agent with verbatim-verified conflict detection, information-gap reporting, deterministic confidence split, and bundle-version propagation.
- **Backend API (M5):** FastAPI under `/api/v1` — brief/analyze/compare endpoints, async producer jobs, bearer auth with hashed keys, rate limiting, request ids, graceful shutdown, Prometheus metrics, OpenAPI docs; Dockerfile + compose with readiness healthcheck.
- **Production hardening (M5.5):** pip-tools pinned dependencies (`requirements.in`/`requirements-dev.in` → compiled pins), Ruff + Black + pragmatic mypy gate (84 source files clean), pre-commit hooks, GitHub Actions CI (lint → typecheck → tests → validator → pip-audit → Docker build), Dependabot, and this changelog.

### Security

- API keys stored hashed only; secrets never logged; 170-test offline suite verifies error envelopes, auth enforcement, and no-leak logging.

[1.0.0]: https://github.com/JustXutkarsh/OKF/releases/tag/v1.0.0
