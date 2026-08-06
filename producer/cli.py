"""Command line interface for the producer agent.

Fixed pipeline order: search → evidence → draft → update model → render →
stage-and-validate → atomic write. The bundle is never modified before
validation passes. Runs are stateless single processes with all settings
from the environment, so cron/systemd (and later Docker) can invoke them
unchanged. Injectable clients and clock keep tests fully deterministic.

Exit codes: 0 success/no-op · 1 unexpected producer error · 2 CLI misuse ·
3 configuration error · 4 external provider failure · 5 bundle validation
failure · 6 filesystem failure.
"""

from __future__ import annotations

import argparse
from datetime import date
from typing import Any

from producer import prompts
from producer.config import (
    concept_relpath,
    get_concept,
    load_config,
    load_registry,
    resolve_window,
)
from producer.evidence import build_evidence
from producer.exceptions import (
    ConfigError,
    LLMResponseError,
    ProducerError,
    RegistryError,
    SearchError,
    ValidationFailure,
)
from producer.models import Document, ProducerConfig
from producer.observability import StageTimer, configure_logging, log_event
from producer.renderer import render_document
from producer.search import TavilySearch
from producer.summarizer import Summarizer
from producer.updater import build_update, has_entry_for, load_document
from producer.validator_adapter import validate_staged
from producer.writer import write_atomic
from validator.reporter import format_human

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 3
EXIT_EXTERNAL = 4
EXIT_VALIDATION = 5
EXIT_FILESYSTEM = 6


def exit_code_for(exc: BaseException) -> int:
    """Map one failure to its documented exit code."""

    if isinstance(exc, ValidationFailure):
        return EXIT_VALIDATION
    if isinstance(exc, (ConfigError, RegistryError)):
        return EXIT_CONFIG
    if isinstance(exc, (SearchError, LLMResponseError)):
        return EXIT_EXTERNAL
    if isinstance(exc, OSError):
        return EXIT_FILESYSTEM
    return EXIT_ERROR


def main(argv: list[str] | None = None) -> int:
    """Run the producer CLI."""

    parser = argparse.ArgumentParser(prog="producer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update", help="Update tracked concept(s).")
    update_parser.add_argument("concept_id", nargs="?", help="Concept id from the registry.")
    update_parser.add_argument(
        "--all", action="store_true", help="Update every registered concept."
    )
    update_parser.add_argument("--lookback-days", type=int, default=None)
    update_parser.add_argument("--max-results", type=int, default=None)
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full pipeline including validation, but write nothing.",
    )

    args = parser.parse_args(argv)
    if bool(args.concept_id) == args.all:
        parser.error("Provide exactly one of <concept-id> or --all.")

    label = args.concept_id or "all"
    try:
        config = load_config()
        configure_logging(config.log_level)

        if args.all:
            reports, code = run_all(config=config, dry_run=args.dry_run)
            print("\n".join(reports))
            return code

        report = run(
            args.concept_id,
            config=config,
            lookback_days=args.lookback_days,
            max_results=args.max_results,
            dry_run=args.dry_run,
        )
        print(report)
        return EXIT_OK
    except ValidationFailure as exc:
        print(format_human(exc.result))
        print("\nBundle not modified.")
        log_event("run.failed", concept=label, error_type="ValidationFailure")
        return EXIT_VALIDATION
    except (ProducerError, OSError) as exc:
        if isinstance(exc, OSError):
            print(f"✖ Filesystem error: {exc}")
        else:
            print(f"✖ {exc}")
        log_event("run.failed", concept=label, error_type=type(exc).__name__)
        return exit_code_for(exc)


def run_all(
    *,
    config: ProducerConfig,
    search_client: Any = None,
    summarizer: Any = None,
    dry_run: bool = False,
    today: date | None = None,
) -> tuple[list[str], int]:
    """Update every registered concept; continue past per-concept failures.

    Returns per-concept report lines plus the highest-severity exit code,
    so a scheduler sees one code for the whole batch.
    """

    registry = load_registry(config.registry_path)
    log_event("run_all.start", concepts=len(registry))
    reports: list[str] = []
    worst = EXIT_OK
    for concept_id in sorted(registry):
        try:
            reports.append(
                run(
                    concept_id,
                    config=config,
                    search_client=search_client,
                    summarizer=summarizer,
                    dry_run=dry_run,
                    today=today,
                )
            )
        except (ProducerError, OSError) as exc:
            worst = max(worst, exit_code_for(exc))
            reports.append(f"✖ {concept_id}: {exc}")
            log_event("run.failed", concept=concept_id, error_type=type(exc).__name__)
    outcome = "ok" if worst == EXIT_OK else f"errors (exit {worst})"
    reports.append(f"— update --all: {len(registry)} concept(s) processed, {outcome}.")
    return reports, worst


def run(
    concept_id: str,
    *,
    config: ProducerConfig | None = None,
    search_client: Any = None,
    summarizer: Any = None,
    lookback_days: int | None = None,
    max_results: int | None = None,
    dry_run: bool = False,
    today: date | None = None,
) -> str:
    """Execute the full producer pipeline for one concept; return a report."""

    config = config or load_config()
    if not config.bundle_path.is_dir():
        raise ConfigError(f"Bundle path does not exist: {config.bundle_path}")

    registry = load_registry(config.registry_path)
    spec = get_concept(registry, concept_id)
    relative_path = concept_relpath(spec)
    target = config.bundle_path / relative_path
    today_str = (today or date.today()).isoformat()

    log_event("run.start", concept=concept_id, dry_run=dry_run)
    total = StageTimer()
    total.__enter__()

    def complete(outcome: str, report: str) -> str:
        log_event("run.complete", concept=concept_id, outcome=outcome, total_ms=total.elapsed_ms())
        return report

    existing: Document | None = None
    if target.is_file():
        existing = load_document(target.read_text(encoding="utf-8"))
        # Same-day check before any API call: no spend on a no-op.
        if has_entry_for(existing, today_str):
            return complete("noop", f"• {concept_id}: already current for {today_str}; no changes.")

    days, limit = resolve_window(spec, config, lookback_days, max_results)

    search_client = search_client or TavilySearch(config)
    with StageTimer() as stage:
        raw_results = search_client.search(spec.search_query, days, limit)
    log_event(
        "stage",
        concept=concept_id,
        stage="search",
        duration_ms=stage.duration_ms,
        results=len(raw_results),
    )

    evidence = build_evidence(raw_results, limit)
    if not evidence:
        return complete(
            "noop", f"• {concept_id}: no evidence in the last {days} day(s); no changes."
        )

    summarizer = summarizer or Summarizer(config)
    latest = existing.developments[0] if existing and existing.developments else None
    user_prompt = prompts.build_user_prompt(
        title=spec.title,
        current_summary=existing.summary if existing else None,
        latest_development_date=latest.date if latest else None,
        latest_development=latest.text if latest else None,
        evidence=evidence,
    )
    with StageTimer() as stage:
        draft = summarizer.draft(prompts.SYSTEM_PROMPT, user_prompt)
    log_event("stage", concept=concept_id, stage="llm", duration_ms=stage.duration_ms)

    updated = build_update(existing, spec, draft, evidence, today=today_str)
    if updated is None:  # defensive; the early check above normally catches this
        return complete("noop", f"• {concept_id}: already current for {today_str}; no changes.")

    content = render_document(updated)
    with StageTimer() as stage:
        validation = validate_staged(config.bundle_path, relative_path, content)
    log_event(
        "stage",
        concept=concept_id,
        stage="validate",
        duration_ms=stage.duration_ms,
        ok=validation.ok,
    )
    if not validation.ok:
        raise ValidationFailure(validation)

    sources_added = len(updated.sources) - (len(existing.sources) if existing else 0)
    action = "update" if existing else "creation"

    lines: list[str] = []
    if dry_run:
        lines.append(f"✔ Dry run — {action} for {concept_id} validated; nothing written.")
    else:
        with StageTimer() as stage:
            write_atomic(target, content)
        log_event("stage", concept=concept_id, stage="write", duration_ms=stage.duration_ms)
        lines.append(f"✔ {action.capitalize()} applied — {concept_id}")
    lines.append(f"File: {relative_path}")
    lines.append(f"Evidence: {len(evidence)} retained ({len(raw_results)} raw)")
    lines.append(f"Sources added: {sources_added}")
    lines.append(f"Confidence: {updated.confidence}")
    lines.append(f"Validation: passed ({validation.checked} documents checked)")
    return complete("dry-run" if dry_run else action, "\n".join(lines))
