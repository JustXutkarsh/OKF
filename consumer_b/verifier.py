"""Deterministic conflict verification against retrieved documents only.

A conflict is valid ONLY when both quoted snippets are found verbatim
(whitespace-normalized) inside the referenced retrieved documents. The
verifier never scans the whole bundle, never fails the request: an
unverifiable conflict is discarded, its reason returned for logging, and
processing continues.
"""

from __future__ import annotations

from consumer_b.models import BundleDocument, ConflictClaim, ResolvedConflict


def verify_conflicts(
    conflicts: list[ConflictClaim],
    documents: list[BundleDocument],
) -> tuple[list[ResolvedConflict], list[str]]:
    """Return (verified conflicts, discard reasons)."""

    verified: list[ResolvedConflict] = []
    discarded: list[str] = []
    seen: set[tuple] = set()
    for claim in conflicts:
        key = (
            tuple(claim.documents),
            " ".join(claim.supporting_text.split()),
            " ".join(claim.conflicting_text.split()),
        )
        if key in seen:
            discarded.append(f"{claim.description[:60]!r}: duplicate conflict claim")
            continue
        seen.add(key)
        if any(index < 1 or index > len(documents) for index in claim.documents):
            discarded.append(
                f"{claim.description[:60]!r}: document index out of range {claim.documents}"
            )
            continue
        referenced = [documents[index - 1] for index in claim.documents]
        if not any(
            _contains_verbatim(doc.searchable_text(), claim.supporting_text) for doc in referenced
        ):
            discarded.append(
                f"{claim.description[:60]!r}: supporting_text not found verbatim in bundle"
            )
            continue
        if not any(
            _contains_verbatim(doc.searchable_text(), claim.conflicting_text) for doc in referenced
        ):
            discarded.append(
                f"{claim.description[:60]!r}: conflicting_text not found verbatim in bundle"
            )
            continue
        verified.append(
            ResolvedConflict(
                description=claim.description,
                document_ids=[doc.id for doc in referenced],
                supporting_text=claim.supporting_text,
                conflicting_text=claim.conflicting_text,
            )
        )
    return verified, discarded


def _contains_verbatim(haystack: str, needle: str) -> bool:
    """Whitespace-normalized verbatim containment."""

    return " ".join(needle.split()) in " ".join(haystack.split())
