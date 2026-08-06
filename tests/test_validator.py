"""Unit tests for the deterministic OKF validator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validator.cli import main
from validator.validator import validate_bundle

VALID_DOC = """---
schema_version: okf-geopolitics/v1
id: nato
type: concept
title: NATO
resource: actors
created_at: 2026-08-06
last_updated: 2026-08-06
tags: [actor]
related: [ukraine-russia-frontline]
confidence: verified
---

## Summary

Current summary.

## Developments

### 2026-08-06

Initial seed.

## Key Actors

- NATO

## Sources

- title: Example source
  url: https://example.com/source
  accessed: 2026-08-06
  note: Example source.
"""

RELATED_DOC = (
    VALID_DOC.replace(
        "id: nato",
        "id: ukraine-russia-frontline",
    )
    .replace(
        "title: NATO",
        "title: Ukraine-Russia Frontline",
    )
    .replace(
        "resource: actors",
        "resource: conflicts",
    )
    .replace(
        "related: [ukraine-russia-frontline]",
        "related: [nato]",
    )
)


class ValidatorTests(unittest.TestCase):
    """Focused validation rule coverage."""

    def test_missing_field(self) -> None:
        """Reports missing required fields."""

        with bundle({"actors/nato.md": VALID_DOC.replace("confidence: verified\n", "")}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF003")

    def test_duplicate_id(self) -> None:
        """Reports duplicate document ids."""

        second = VALID_DOC.replace("title: NATO", "title: NATO Copy")
        with bundle({"actors/nato.md": VALID_DOC, "actors/nato-copy.md": second}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF006")

    def test_invalid_yaml(self) -> None:
        """Reports invalid YAML syntax."""

        doc = VALID_DOC.replace("tags: [actor]", "tags: [actor")
        with bundle({"actors/nato.md": doc}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF002")

    def test_missing_section(self) -> None:
        """Reports missing required markdown sections."""

        doc = VALID_DOC.replace("## Key Actors\n\n- NATO\n\n", "")
        with bundle({"actors/nato.md": doc}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF010")

    def test_invalid_date(self) -> None:
        """Reports invalid ISO dates."""

        doc = VALID_DOC.replace("last_updated: 2026-08-06", "last_updated: 08/06/2026")
        with bundle({"actors/nato.md": doc}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF012")

    def test_broken_related_link(self) -> None:
        """Reports related ids that do not exist."""

        doc = VALID_DOC.replace("related: [ukraine-russia-frontline]", "related: [missing-id]")
        with bundle({"actors/nato.md": doc}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF007")

    def test_wrong_folder(self) -> None:
        """Reports folder/resource mismatches."""

        with bundle({"policy/nato.md": VALID_DOC}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF009")

    def test_wrong_filename(self) -> None:
        """Reports filename/id mismatches."""

        with bundle({"actors/not-nato.md": VALID_DOC}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF008")

    def test_empty_sources(self) -> None:
        """Reports empty Sources sections."""

        doc = VALID_DOC.replace(
            "- title: Example source\n"
            "  url: https://example.com/source\n"
            "  accessed: 2026-08-06\n"
            "  note: Example source.\n",
            "",
        )
        with bundle({"actors/nato.md": doc}) as root:
            result = validate_bundle(root)
        self.assert_has_code(result, "OKF011")

    def test_json_output(self) -> None:
        """CLI supports deterministic JSON output."""

        with bundle(
            {"actors/nato.md": VALID_DOC, "conflicts/ukraine-russia-frontline.md": RELATED_DOC}
        ) as root:
            with captured_stdout() as output:
                exit_code = main(["validate", str(root), "--format", "json"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["checked"], 2)

    def assert_has_code(self, result, code: str) -> None:
        """Assert a validation result includes a specific error code."""

        self.assertIn(code, {error.code for error in result.errors})


class bundle:
    """Temporary OKF bundle fixture."""

    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.tmp: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None

    def __enter__(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, text in self.files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return self.root

    def __exit__(self, *args) -> None:
        assert self.tmp is not None
        self.tmp.cleanup()


class captured_stdout:
    """Capture stdout without test framework dependencies."""

    def __enter__(self):
        import io
        import sys

        self.original = sys.stdout
        self.buffer = io.StringIO()
        sys.stdout = self.buffer
        return self.buffer

    def __exit__(self, *args) -> None:
        import sys

        sys.stdout = self.original


if __name__ == "__main__":
    unittest.main()
