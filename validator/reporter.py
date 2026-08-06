"""Human and JSON reporting for validator results."""

from __future__ import annotations

import json

from validator.models import ValidationResult


def format_human(result: ValidationResult) -> str:
    """Format a validation result for terminal users."""

    if result.ok:
        return "✔ Validation successful"

    blocks = ["✖ Validation failed", ""]
    for error in result.errors:
        blocks.extend(
            [
                f"Code: {error.code}",
                "File:",
                error.file,
                "",
                "Line:",
                str(error.line) if error.line is not None else "unknown",
                "",
                "Rule:",
                error.rule,
            ]
        )
        if error.field:
            blocks.extend(["", "Field:", error.field])
        blocks.extend(["", "Suggested fix:", error.suggested_fix, ""])
    return "\n".join(blocks).rstrip()


def format_json(result: ValidationResult) -> str:
    """Format a validation result as deterministic JSON."""

    return json.dumps(result.model_dump(), indent=2, sort_keys=True)
