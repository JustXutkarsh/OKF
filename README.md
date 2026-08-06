# OKF Geopolitics Briefing Bundle

This repository starts with the M0 seed bundle for the Cross-Agent OKF Knowledge Exchange project.

The `okf/` directory is the portable knowledge layer. It is intentionally plain markdown with YAML frontmatter so it can be read by humans, reviewed in git, and consumed by independent agents without a shared database, SDK, API, vector store, or embedding model.

## Bundle Layout

```text
okf/
  actors/
  conflicts/
  economics/
  policy/
```

Each concept is one markdown file. The file path is useful for navigation, but metadata relationships use stable concept IDs.

## Required Frontmatter

```yaml
---
id: stable-concept-id
type: concept
title: Human-readable title
tags: [example, tags]
resource: category
last_updated: YYYY-MM-DD
related: [other-stable-id]
---
```

M0 requires every concept document to include an `id` field. Future validator work will resolve `related` IDs to files.

## Body Convention

Each concept document uses:

- `Summary`
- `Developments`
- `Key Actors`
- `Sources`

The `Summary` section is the current quick-read ground truth. `Developments` is append-only by date once producer automation exists in a later milestone.
