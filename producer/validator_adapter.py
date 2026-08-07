"""Stage a rendered document into a temporary bundle copy and validate it.

Validation is the final gate before any write. The validator's public API
is directory-based (and cross-document rules need the whole bundle), so the
bundle is copied into a temporary directory, the rendered document is staged
there, and validation runs against that copy. This module never touches the
real bundle.

Debugging hooks (observability only — behavior unchanged):
* every validation error is logged individually before callers react;
* when OKF_KEEP_FAILED_STAGE=true, the staged bundle is kept on disk and
  its full path is logged and returned for inspection.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from producer.observability import log_event
from validator.models import ValidationResult
from validator.validator import validate_bundle

_KEEP_AFTER_STAGE_ENV = "OKF_KEEP_FAILED_STAGE"
_TRUTHY = {"1", "true", "yes", "on"}


def keep_staged_bundle() -> bool:
    """Return True when OKF_KEEP_FAILED_STAGE requests preserving staged bundles."""

    return os.environ.get(_KEEP_AFTER_STAGE_ENV, "").strip().lower() in _TRUTHY


def _log_errors(result: ValidationResult) -> None:
    """Emit one structured log line per validation error."""

    for error in result.errors:
        log_event(
            "validation.error",
            code=error.code,
            file=error.file,
            line=error.line,
            rule=error.rule,
        )


def validate_staged(
    bundle_path: Path, relative_path: str, content: str
) -> tuple[ValidationResult, str | None]:
    """Validate the bundle as it would look with the staged document written.

    Returns the result plus the retained bundle path when
    OKF_KEEP_FAILED_STAGE=true, otherwise None.
    """

    if keep_staged_bundle():
        # Kept for post-mortem inspection; caller cleans up later if needed.
        tmp = tempfile.mkdtemp(prefix="okf-stage-")
        cleanup = None
    else:
        td = tempfile.TemporaryDirectory(prefix="okf-stage-")
        tmp = td.name
        cleanup = td.cleanup

    try:
        staged_root = Path(tmp) / bundle_path.name
        shutil.copytree(bundle_path, staged_root)
        staged_file = staged_root / relative_path
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.write_text(content, encoding="utf-8")
        result = validate_bundle(staged_root)

        if not result.ok:
            _log_errors(result)
        if cleanup is None:
            log_event("validation.stage_kept", path=str(staged_root), ok=result.ok)

        return result, None if cleanup is not None else str(staged_root)
    finally:
        if cleanup is not None:
            cleanup()
