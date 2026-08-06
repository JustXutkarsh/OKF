"""Consumer B CLI: parse arguments, call ConsumerService, print, exit code.

Exit code mapping (each error category maps to exactly one code):
  0  ok or not-covered · 1 unexpected internal error · 2 misuse/empty
     question · 3 configuration · 4 LLM provider failure or timeout ·
     5 malformed bundle · 6 filesystem error.
Stack traces are never shown to end users.
"""

from __future__ import annotations

import argparse
import logging

from consumer_b.config import load_config
from consumer_b.exceptions import (
    ConfigError,
    ConsumerError,
    DocumentReadError,
    FilesystemError,
    LLMResponseError,
    RetrievalError,
)
from consumer_b.exceptions import TimeoutError as ProviderTimeoutError
from consumer_b.observability import StageTimer, configure_logging, log_event
from consumer_b.renderer import render_json, render_text
from consumer_b.service import ConsumerService

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_PROVIDER = 4
EXIT_BUNDLE = 5
EXIT_FILESYSTEM = 6


def exit_code_for(exc: BaseException) -> int:
    """Map one failure category to exactly one documented exit code."""

    if isinstance(exc, RetrievalError):
        return EXIT_USAGE
    if isinstance(exc, ConfigError):
        return EXIT_CONFIG
    if isinstance(exc, (LLMResponseError, ProviderTimeoutError)):
        return EXIT_PROVIDER
    if isinstance(exc, DocumentReadError):
        return EXIT_BUNDLE
    if isinstance(exc, FilesystemError):
        return EXIT_FILESYSTEM
    return EXIT_ERROR


def main(argv: list[str] | None = None) -> int:
    """Run the Consumer B CLI."""

    parser = argparse.ArgumentParser(prog="consumer_b")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze", help="Critically analyze a question from the OKF bundle."
    )
    analyze_parser.add_argument("question", nargs="+", help="Natural-language question.")
    analyze_parser.add_argument("--json", dest="json_output", action="store_true")
    analyze_parser.add_argument("--max-docs", type=int, default=None)

    args = parser.parse_args(argv)
    if args.max_docs is not None and args.max_docs < 1:
        parser.error("--max-docs must be >= 1")

    try:
        config = load_config()
        configure_logging(config.log_level)

        report = ConsumerService(config).analyze(" ".join(args.question), max_docs=args.max_docs)

        with StageTimer() as stage:
            output = render_json(report) if args.json_output else render_text(report)
        log_event("stage", stage="render", duration_ms=stage.duration_ms)

        print(output)
        return EXIT_OK
    except ConsumerError as exc:
        print(f"✖ {exc}")
        log_event("analyze.failed", error_type=type(exc).__name__)
        return exit_code_for(exc)
    except Exception:
        logging.getLogger("consumer_b").debug("unexpected internal error", exc_info=True)
        print("✖ Unexpected internal error.")
        return EXIT_ERROR
