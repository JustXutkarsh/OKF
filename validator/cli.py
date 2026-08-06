"""Command line interface for the deterministic OKF validator."""

from __future__ import annotations

import argparse
from pathlib import Path

from validator.reporter import format_human, format_json
from validator.validator import validate_bundle


def main(argv: list[str] | None = None) -> int:
    """Run the validator CLI."""

    parser = argparse.ArgumentParser(prog="validator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an OKF bundle.")
    validate_parser.add_argument("path", help="Path to the okf directory.")
    validate_parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format.",
    )

    args = parser.parse_args(argv)
    if args.command != "validate":
        parser.error("Unsupported command.")

    bundle_path = Path(args.path)
    if not bundle_path.exists() or not bundle_path.is_dir():
        parser.error(f"Bundle path does not exist or is not a directory: {bundle_path}")

    result = validate_bundle(bundle_path)
    if args.format == "json":
        print(format_json(result))
    else:
        print(format_human(result))
    return 0 if result.ok else 1
