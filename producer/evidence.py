"""Deterministic evidence normalization, deduplication, and ranking.

No LLM involvement: provider items go in, clean ranked Evidence comes out.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlparse

from producer.models import Evidence

NOTE_MAX_CHARS = 180


def normalize_url(url: str) -> str:
    """Return a canonical key for URL deduplication (host + path, no scheme)."""

    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def url_domain(url: str) -> str:
    """Return the lowercase domain of a URL (used by the confidence rule)."""

    return urlparse(url.strip()).netloc.lower()


def make_note(snippet: str) -> str:
    """Derive a one-line source note from a search snippet, deterministically."""

    text = " ".join(snippet.split())
    if len(text) <= NOTE_MAX_CHARS:
        return text
    truncated = text[:NOTE_MAX_CHARS].rsplit(" ", 1)[0].rstrip(",.;:")
    return truncated + "."


def _published_key(value: str | None) -> date:
    """Parse a provider publication date; unknown dates sort oldest."""

    if value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return date.min


def normalize_results(raw_items: list[dict[str, Any]]) -> list[Evidence]:
    """Drop malformed items, keep usable fields, dedupe by canonical URL."""

    seen: set[str] = set()
    hits: list[Evidence] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        title = item.get("title")
        if not isinstance(url, str) or not url.strip():
            continue
        if not isinstance(title, str) or not title.strip():
            continue
        key = normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        published = item.get("published_date")
        snippet = item.get("content") or ""
        hits.append(
            Evidence(
                title=title.strip(),
                url=url.strip(),
                published_date=published if isinstance(published, str) and published else None,
                snippet=str(snippet),
                note=make_note(str(snippet)),
            )
        )
    return hits


def rank_results(hits: list[Evidence]) -> list[Evidence]:
    """Rank by publication date, newest first (stable, deterministic)."""

    return sorted(hits, key=lambda hit: _published_key(hit.published_date), reverse=True)


def build_evidence(raw_items: list[dict[str, Any]], max_results: int) -> list[Evidence]:
    """Full pipeline: normalize → dedupe → rank → cap at max_results."""

    return rank_results(normalize_results(raw_items))[:max_results]
