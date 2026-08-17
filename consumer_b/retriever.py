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
    "by from with about between into over through under above below across against "
    "what how why when who whom which whose does do did will would can could should "
    "has have had this that these those current latest recent now today tell me give "
    "explain describe compare main major strategic economic associated actors ability "
    "influence risk risks affect affects effect effects impact impacts situation "
    "overview dynamics factors factor implications implication role roles status "
    "tensions tension disruption disruptions dispute disputes disputed".split()
)

# Common geographic, military, and institutional descriptors that frequently collide
# across clusters when separated from their core named entities.
MODIFIERS = frozenset(
    "strait sea gulf bay canal corridor channel river mountain pass sector island islands "
    "forces military command fleet defense security operations frontline border "
    "treaty agreement convention resolution accord policy doctrine supply chain chains".split()
)

# Recognized geopolitical theatres / entity clusters for
# deterministic multi-topic query decomposition
THEATRE_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    (
        "Taiwan",
        re.compile(r"\b(taiwan|taiwan\s+strait|taipei|tsmc)\b", re.IGNORECASE),
        "Taiwan Taiwan Strait",
    ),
    (
        "Strait of Hormuz",
        re.compile(r"\b(hormuz|strait\s+of\s+hormuz|persian\s+gulf|irgc)\b", re.IGNORECASE),
        "Strait of Hormuz Hormuz",
    ),
    (
        "Gaza",
        re.compile(r"\b(gaza|hamas|philadelphi|rafah)\b", re.IGNORECASE),
        "Gaza",
    ),
    (
        "Israel-Lebanon",
        re.compile(r"\b(israel[- ]lebanon|lebanon|hezbollah|unscr\s+1701|litani)\b", re.IGNORECASE),
        "Israel Lebanon Hezbollah",
    ),
    (
        "India-China",
        re.compile(
            r"\b(india[- ]china|sino[- ]indian|arunachal|arunachal\s+pradesh|lac|zangnan)\b",
            re.IGNORECASE,
        ),
        "India China Arunachal Pradesh LAC",
    ),
    (
        "Red Sea",
        re.compile(r"\b(red\s+sea|houthi|bab\s+el[- ]mandeb|yemen)\b", re.IGNORECASE),
        "Red Sea Houthi",
    ),
    (
        "NATO",
        re.compile(r"\b(nato|eastern\s+flank)\b", re.IGNORECASE),
        "NATO",
    ),
    (
        "US-China Tariffs",
        re.compile(r"\b(tariffs?|export\s+controls?)\b", re.IGNORECASE),
        "US-China tariffs export controls",
    ),
]

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens without stopwords (question or field text)."""

    return [t for t in _TOKEN_PATTERN.findall(text.lower()) if t not in STOPWORDS]


def _raw_tokens(text: str) -> list[str]:
    """All lowercase alphanumeric tokens without stopword stripping."""

    return _TOKEN_PATTERN.findall(text.lower())


def _normalized(text: str) -> str:
    """Lowercase text with punctuation collapsed to single spaces."""

    return " ".join(_TOKEN_PATTERN.findall(text.lower()))


def detect_topics(question: str) -> list[tuple[str, str]]:
    """Deterministically detect recognized geopolitical theatres/entities in the question."""

    return [
        (name, topic_q) for name, pattern, topic_q in THEATRE_PATTERNS if pattern.search(question)
    ]


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
    """Bonus when adjacent question-token bigrams appear in title, id, or tags."""

    q_toks = tokenize(question)
    if len(q_toks) < 2:
        return 0

    # 1. Check adjacent question tokens in tokenized title, id, or tags
    for first, second in zip(q_toks, q_toks[1:]):
        t_toks = tokenize(entry.title)
        for i in range(len(t_toks) - 1):
            if t_toks[i] == first and t_toks[i + 1] == second:
                return PHRASE_WEIGHT

        id_toks = tokenize(entry.id)
        for i in range(len(id_toks) - 1):
            if id_toks[i] == first and id_toks[i + 1] == second:
                return PHRASE_WEIGHT

        for tag in entry.tags:
            tag_t = tokenize(tag)
            for i in range(len(tag_t) - 1):
                if tag_t[i] == first and tag_t[i + 1] == second:
                    return PHRASE_WEIGHT

    # 2. Check contiguous raw bigrams in raw title text (handles stopwords like "of")
    t_raw = " ".join(_raw_tokens(entry.title))
    for i in range(len(q_toks) - 1):
        bigram = f"{q_toks[i]} {q_toks[i + 1]}"
        if bigram in t_raw or bigram in entry.id:
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


def select_single_topic(
    catalog: list[CatalogEntry], question: str, max_docs: int
) -> RetrievalResult:
    """Score the catalog for a single query scope, rank deterministically, return selection."""

    tokens = tokenize(question)
    rows: list[tuple[CatalogEntry, RankingEntry]] = []
    for entry in catalog:
        title = title_score(tokens, entry)
        tags = tag_score(tokens, entry)
        ident = id_score(tokens, entry)
        resource = resource_score(tokens, entry)
        phrase = phrase_bonus(question, entry)

        base_total = title + tags + ident + resource + phrase
        if base_total > 0:
            all_matched = (
                (set(tokens) & set(tokenize(entry.title)))
                | (set(tokens) & {token for tag in entry.tags for token in tokenize(tag)})
                | (set(tokens) & set(tokenize(entry.id)))
                | (set(tokens) & set(tokenize(entry.resource)))
            )
            distinctive = [t for t in all_matched if t not in MODIFIERS]
            entity_bonus = 10 if distinctive else 0
            breadth_bonus = (
                4 * (len(all_matched) - 1) if len(all_matched) > 1 and distinctive else 0
            )

            total = base_total + entity_bonus + breadth_bonus
            rows.append(
                (
                    entry,
                    RankingEntry(
                        document_id=entry.id,
                        title_score=title,
                        tag_score=tags,
                        id_score=ident,
                        resource_score=resource,
                        phrase_bonus=phrase + entity_bonus + breadth_bonus,
                        total_score=total,
                    ),
                )
            )

    rows.sort(key=lambda item: (-item[1].total_score, item[1].document_id))

    if not rows:
        return RetrievalResult(candidate_count=len(catalog), selected=[], ranking=[])

    top_score = rows[0][1].total_score
    cutoff = max(4, int(top_score * 0.35)) if top_score >= 10 else 1
    selected_docs = [entry for entry, rank in rows if rank.total_score >= cutoff][:max_docs]

    return RetrievalResult(
        candidate_count=len(catalog),
        selected=selected_docs,
        ranking=[rank for _, rank in rows],
    )


def select(catalog: list[CatalogEntry], question: str, max_docs: int = 3) -> RetrievalResult:
    """Deterministic lexical retriever with multi-topic query decomposition."""

    topics = detect_topics(question)
    if len(topics) >= 2:
        # Multi-theatre comparative query: decompose into deterministic topic scopes
        merged_selected: list[CatalogEntry] = []
        seen_ids: set[str] = set()
        merged_ranking: list[RankingEntry] = []
        seen_rank_ids: set[str] = set()

        per_topic_limit = max(2, max_docs)
        for _, topic_query in topics:
            topic_res = select_single_topic(catalog, topic_query, per_topic_limit)
            for doc in topic_res.selected:
                if doc.id not in seen_ids:
                    seen_ids.add(doc.id)
                    merged_selected.append(doc)
            for rank in topic_res.ranking:
                if rank.document_id not in seen_rank_ids:
                    seen_rank_ids.add(rank.document_id)
                    merged_ranking.append(rank)

        merged_ranking.sort(key=lambda item: (-item.total_score, item.document_id))
        return RetrievalResult(
            candidate_count=len(catalog),
            selected=merged_selected,
            ranking=merged_ranking,
        )

    return select_single_topic(catalog, question, max_docs)
