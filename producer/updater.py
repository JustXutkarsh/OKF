"""Deterministic document updates: the only module allowed to change content.

Mutations per run: replace Summary, prepend one dated Development entry,
merge Sources, bump last_updated, recompute confidence. Everything else
(schema_version, id, type, title, resource, tags, created_at, related,
key_actors, prior development entries) is preserved untouched.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import yaml

from producer.config import (
    CONFIDENCE_MIXED_MIN_INDEPENDENT,
    CONFIDENCE_VERIFIED_MIN_INDEPENDENT,
)
from producer.evidence import normalize_url, url_domain
from producer.exceptions import DocumentParseError
from producer.models import (
    ConceptSpec,
    DevelopmentEntry,
    Document,
    Evidence,
    LLMDraft,
    SourceEntry,
)

SECTION_PATTERN = re.compile(r"^## +(.+?) *$", re.MULTILINE)
DEVELOPMENT_PATTERN = re.compile(r"^### +(.+?) *$", re.MULTILINE)

KNOWN_FRONTMATTER_FIELDS = frozenset(
    {
        "schema_version",
        "id",
        "type",
        "title",
        "resource",
        "tags",
        "created_at",
        "last_updated",
        "confidence",
        "related",
    }
)


def has_entry_for(document: Document | None, day: str) -> bool:
    """Return True when the document already logs an entry for the date."""

    return document is not None and any(entry.date == day for entry in document.developments)


def compute_confidence(sources: list[SourceEntry]) -> str:
    """Deterministic confidence from independent (unique-domain) sources.

    verified:   >= CONFIDENCE_VERIFIED_MIN_INDEPENDENT unique domains
    mixed:      >= CONFIDENCE_MIXED_MIN_INDEPENDENT unique domains
    otherwise:  unverified
    """

    domains = {url_domain(entry.url) for entry in sources if entry.url}
    if len(domains) >= CONFIDENCE_VERIFIED_MIN_INDEPENDENT:
        return "verified"
    if len(domains) >= CONFIDENCE_MIXED_MIN_INDEPENDENT:
        return "mixed"
    return "unverified"


def merge_sources(
    existing: list[SourceEntry],
    evidence: list[Evidence],
    *,
    accessed: str,
) -> list[SourceEntry]:
    """Append evidence-backed sources not already present (URL-deduped)."""

    merged = list(existing)
    seen = {normalize_url(entry.url) for entry in existing}
    for hit in evidence:
        key = normalize_url(hit.url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            SourceEntry(title=hit.title, url=hit.url, accessed=accessed, note=hit.note)
        )
    return merged


def build_update(
    document: Document | None,
    spec: ConceptSpec,
    draft: LLMDraft,
    evidence: list[Evidence],
    *,
    today: str,
) -> Document | None:
    """Apply one producer run to a document (or create it when missing).

    Returns None when the document already logs a development for `today`:
    the run is a no-op and the file must not be touched. Never rewrites,
    reorders, or duplicates prior development entries.
    """

    if has_entry_for(document, today):
        return None

    entry = DevelopmentEntry(date=today, text=draft.development.strip())

    if document is None:
        base = Document(
            id=spec.id,
            title=spec.title,
            resource=spec.resource,
            tags=list(spec.tags),
            related=list(spec.related),
            key_actors=list(spec.key_actors),
            created_at=today,
            last_updated=today,
            confidence="",
            summary="",
        )
    else:
        base = document

    sources = merge_sources(base.sources, evidence, accessed=today)
    return base.model_copy(
        update={
            "summary": draft.summary.strip(),
            "developments": [entry, *base.developments],
            "sources": sources,
            "last_updated": today,
            "confidence": compute_confidence(sources),
        }
    )


def load_document(text: str) -> Document:
    """Parse canonical bundle markdown into a Document model.

    Raises DocumentParseError on anything unexpected instead of guessing;
    unknown frontmatter fields are rejected rather than silently dropped.
    """

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise DocumentParseError("Document is missing a YAML frontmatter block.")
    end_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end_index is None:
        raise DocumentParseError("Document frontmatter is not closed with ---.")

    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:end_index])) or {}
    except yaml.YAMLError as exc:
        raise DocumentParseError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise DocumentParseError("Frontmatter must be a YAML mapping.")
    unknown = sorted(set(frontmatter) - KNOWN_FRONTMATTER_FIELDS)
    if unknown:
        raise DocumentParseError(
            f"Unsupported frontmatter fields {unknown}; refusing to drop them silently."
        )

    sections = _split_sections("\n".join(lines[end_index + 1 :]))
    return Document(
        schema_version=frontmatter.get("schema_version", 1),
        id=str(frontmatter.get("id", "")),
        type=str(frontmatter.get("type", "concept")),
        title=str(frontmatter.get("title", "")),
        resource=str(frontmatter.get("resource", "")),
        tags=[str(tag) for tag in (frontmatter.get("tags") or [])],
        created_at=_coerce_date(frontmatter.get("created_at", "")),
        last_updated=_coerce_date(frontmatter.get("last_updated", "")),
        confidence=str(frontmatter.get("confidence", "")),
        related=[str(item) for item in (frontmatter.get("related") or [])],
        summary=sections.get("Summary", "").strip(),
        developments=_parse_developments(sections.get("Developments", "")),
        key_actors=_parse_key_actors(sections.get("Key Actors", "")),
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


def _parse_key_actors(section: str) -> list[str]:
    return [
        line.strip()[2:].strip()
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]


def _parse_sources(section: str) -> list[SourceEntry]:
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
    return [
        SourceEntry(
            title=entry.get("title", ""),
            url=entry.get("url", ""),
            accessed=entry.get("accessed", ""),
            note=entry.get("note", ""),
        )
        for entry in entries
        if entry.get("url")
    ]


def _coerce_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
