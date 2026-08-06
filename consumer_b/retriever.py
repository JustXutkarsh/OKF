"""Deterministic lexical retrieval over the bundle frontmatter catalog.

No embeddings, no vector stores, no semantic search — transparent,
tunable, testable scoring (Consumer B's own copy of the philosophy;
shares no code with Consumer A). Each scoring signal is an independent
function; the total is a plain sum. Ties break on concept id, so
identical questions always produce identical selections.
"""

from __future__ import annotations

import re

from consumer_b.models import CatalogEntry, RankingEntry, RetrievalResult

TITLE_WEIGHT = 4
TAG_WEIGHT = 3
ID_WEIGHT = 2
RESOURCE_WEIGHT = 1
PHRASE_WEIGHT = 5

STOPWORDS = frozenset(
    "a an the and or of in on to for is are was were be been being it its as at "
    "by from with about between what how why when who whom which whose does do "
    "did will would can could should has have had this that these those current "
    "latest recent now today tell me give explain".split()
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens without stopwords (question or field text)."""

    return [t for t in _TOKEN_PATTERN.findall(text.lower()) if t not in STOPWORDS]


def _normalized(text: str) -> str:
    """Lowercase text with punctuation collapsed to single spaces."""

    return " ".join(_TOKEN_PATTERN.findall(text.lower()))


def title_score(question_tokens: list[str], entry: CatalogEntry) -> int:
    """Distinct question tokens present in the document title."""

    return TITLE_WEIGHT * len(set(question_tokens) & set(tokenize(entry.title)))


def tag_score(question_tokens: list[str], entry: CatalogEntry) -> int:
    """Distinct question tokens present in the document tags."""

    tag_tokens = {token for tag in entry.tags for token in tokenize(tag)}
    return TAG_WEIGHT * len(set(question_tokens) & tag_tokens)


def id_score(question_tokens: list[str], entry: CatalogEntry) -> int:
    """Distinct question tokens present in the kebab-case document id."""

    return ID_WEIGHT * len(set(question_tokens) & set(tokenize(entry.id)))


def resource_score(question_tokens: list[str], entry: CatalogEntry) -> int:
    """Distinct question tokens present in the resource folder name."""

    return RESOURCE_WEIGHT * len(set(question_tokens) & set(tokenize(entry.resource)))


def phrase_bonus(question: str, entry: CatalogEntry) -> int:
    """Bonus when any adjacent question-token bigram appears in the title."""

    title_text = _normalized(entry.title)
    tokens = tokenize(question)
    for first, second in zip(tokens, tokens[1:]):
        if f"{first} {second}" in title_text:
            return PHRASE_WEIGHT
    return 0


def total_score(question: str, entry: CatalogEntry) -> int:
    """Full score: the sum of the five independent signal functions."""

    tokens = tokenize(question)
    return (
        title_score(tokens, entry)
        + tag_score(tokens, entry)
        + id_score(tokens, entry)
        + resource_score(tokens, entry)
        + phrase_bonus(question, entry)
    )


def select(catalog: list[CatalogEntry], question: str, max_docs: int) -> RetrievalResult:
    """Score the catalog, rank deterministically, return selection + ranking."""

    tokens = tokenize(question)
    rows: list[tuple[CatalogEntry, RankingEntry]] = []
    for entry in catalog:
        title = title_score(tokens, entry)
        tags = tag_score(tokens, entry)
        ident = id_score(tokens, entry)
        resource = resource_score(tokens, entry)
        phrase = phrase_bonus(question, entry)
        total = title + tags + ident + resource + phrase
        if total > 0:
            rows.append(
                (
                    entry,
                    RankingEntry(
                        document_id=entry.id,
                        title_score=title,
                        tag_score=tags,
                        id_score=ident,
                        resource_score=resource,
                        phrase_bonus=phrase,
                        total_score=total,
                    ),
                )
            )
    rows.sort(key=lambda item: (-item[1].total_score, item[1].document_id))
    return RetrievalResult(
        candidate_count=len(catalog),
        selected=[entry for entry, _ in rows[:max_docs]],
        ranking=[rank for _, rank in rows],
    )
