"""Read-only access to the OKF bundle (Consumer B's own copy).

Two strict access levels, nothing else:
  scan_catalog(bundle_path)  — reads ONLY frontmatter of every document
  read_documents(...)        — reads the body of SELECTED documents only

Never writes, never caches, never preloads bodies, and never touches
validator, producer, or Consumer A code. Consumer B is read-only.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from consumer_b.exceptions import ConfigError, DocumentReadError, FilesystemError
from consumer_b.models import (
    BundleDocument,
    CatalogEntry,
    DevelopmentEntry,
    SourceRef,
)

SECTION_PATTERN = re.compile(r"^## +(.+?) *$", re.MULTILINE)
DEVELOPMENT_PATTERN = re.compile(r"^### +(.+?) *$", re.MULTILINE)


def scan_catalog(bundle_path: Path) -> list[CatalogEntry]:
    """Build the retrieval catalog from frontmatter only.

    Document bodies are never opened here. A malformed bundle (unreadable
    file, invalid YAML, missing id/title, duplicate id) is a hard error —
    Consumer B reports problems instead of guessing around them.
    """

    if not bundle_path.is_dir():
        raise ConfigError(f"Bundle path does not exist: {bundle_path}")

    entries: list[CatalogEntry] = []
    seen_ids: set[str] = set()
    for path in sorted(bundle_path.rglob("*.md")):
        entry = _read_frontmatter_only(path, bundle_path)
        if entry.id in seen_ids:
            raise DocumentReadError(
                f"Malformed bundle: duplicate document id {entry.id!r} ({entry.relative_path})."
            )
        seen_ids.add(entry.id)
        entries.append(entry)
    return entries


def _read_frontmatter_only(path: Path, bundle_path: Path) -> CatalogEntry:
    """Parse one document's frontmatter without reading its body."""

    relative_path = path.relative_to(bundle_path).as_posix()
    try:
        with path.open(encoding="utf-8") as handle:
            first = handle.readline()
            if first.strip() != "---":
                raise DocumentReadError(
                    f"Malformed bundle document (no frontmatter): {relative_path}"
                )
            yaml_lines: list[str] = []
            for line in handle:
                if line.strip() == "---":
                    break
                yaml_lines.append(line)
            else:
                raise DocumentReadError(
                    f"Malformed bundle document (unclosed frontmatter): {relative_path}"
                )
    except OSError as exc:
        raise FilesystemError(f"Cannot read bundle document {relative_path}: {exc}") from exc

    try:
        frontmatter = yaml.safe_load("".join(yaml_lines)) or {}
    except yaml.YAMLError as exc:
        raise DocumentReadError(f"Invalid YAML frontmatter in {relative_path}: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise DocumentReadError(f"Invalid YAML frontmatter in {relative_path}: not a mapping.")

    doc_id = frontmatter.get("id")
    title = frontmatter.get("title")
    if not doc_id or not title:
        raise DocumentReadError(
            f"Malformed bundle document {relative_path}: frontmatter requires id and title."
        )
    return CatalogEntry(
        id=str(doc_id),
        title=str(title),
        resource=str(frontmatter.get("resource", "")),
        tags=[str(tag) for tag in (frontmatter.get("tags") or [])],
        related=[str(item) for item in (frontmatter.get("related") or [])],
        confidence=_str_or_empty(frontmatter.get("confidence")),
        schema_version=frontmatter.get("schema_version", 1),
        relative_path=relative_path,
    )


def read_documents(bundle_path: Path, entries: list[CatalogEntry]) -> list[BundleDocument]:
    """Read and parse the FULL body of selected documents only."""

    return [_read_document(bundle_path, entry) for entry in entries]


def _read_document(bundle_path: Path, entry: CatalogEntry) -> BundleDocument:
    relative_path = entry.relative_path
    path = bundle_path / relative_path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FilesystemError(f"Cannot read bundle document {relative_path}: {exc}") from exc

    end_index = None
    lines = text.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise DocumentReadError(
            f"Malformed bundle document (unclosed frontmatter): {relative_path}"
        )

    sections = _split_sections("\n".join(lines[end_index + 1 :]))
    return BundleDocument(
        id=entry.id,
        title=entry.title,
        resource=entry.resource,
        relative_path=relative_path,
        summary=sections.get("Summary", "").strip(),
        developments=_parse_developments(sections.get("Developments", "")),
        key_actors=_parse_bullets(sections.get("Key Actors", "")),
        sources=_parse_sources(sections.get("Sources", "")),
    )


def _split_sections(body: str) -> dict[str, str]:
    matches = list(SECTION_PATTERN.finditer(body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1)] = body[match.end() : stop].strip("\n")
    return sections


def _parse_developments(section: str) -> list[DevelopmentEntry]:
    matches = list(DEVELOPMENT_PATTERN.finditer(section))
    entries: list[DevelopmentEntry] = []
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        entries.append(
            DevelopmentEntry(
                date=match.group(1).strip(),
                text=section[match.end() : stop].strip(),
            )
        )
    return entries


def _parse_bullets(section: str) -> list[str]:
    return [
        line.strip()[2:].strip() for line in section.splitlines() if line.strip().startswith("- ")
    ]


def _parse_sources(section: str) -> list[SourceRef]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- title:"):
            current = {"title": stripped.removeprefix("- title:").strip()}
            entries.append(current)
        elif current is not None and line.startswith("  ") and ":" in stripped:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip()
    # Malformed source metadata is handled deterministically: entries
    # without a URL are dropped (a source without a URL is not citable).
    return [
        SourceRef(
            title=entry.get("title", ""),
            url=entry.get("url", ""),
            accessed=entry.get("accessed", ""),
            note=entry.get("note", ""),
        )
        for entry in entries
        if entry.get("url")
    ]


def _str_or_empty(value: object) -> str:
    """Coerce a possibly-malformed scalar (e.g. confidence) to text."""

    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value)
