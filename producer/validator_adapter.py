"""Stage a rendered document into a temporary bundle copy and validate it.

Validation is the final gate before any write. The validator's public API
is directory-based (and cross-document rules need the whole bundle), so the
bundle is copied into a temporary directory, the rendered document is staged
there, and validation runs against that copy. This module never touches the
real bundle.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from validator.models import ValidationResult
from validator.validator import validate_bundle


def validate_staged(bundle_path: Path, relative_path: str, content: str) -> ValidationResult:
    """Validate the bundle as it would look with the staged document written."""

    with tempfile.TemporaryDirectory(prefix="okf-stage-") as tmp:
        staged_root = Path(tmp) / bundle_path.name
        shutil.copytree(bundle_path, staged_root)
        staged_file = staged_root / relative_path
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.write_text(content, encoding="utf-8")
        return validate_bundle(staged_root)
