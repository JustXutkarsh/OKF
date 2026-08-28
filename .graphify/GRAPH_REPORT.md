# OKF Codebase & Intelligence Architecture Graph Report (.graphify)

**Generated:** 2026-08-28T19:25:00.973466+00:00
**Repository:** JustXutkarsh/OKF
**Graph Nodes:** 974 | **Graph Edges:** 1490

---

## 1. Executive Summary

This knowledge graph models the complete **OKF (Open Knowledge Formulation)** architecture:
- **Two-Agent Analysis Pipeline**: Dual-consumer orchestration between Briefing Agent
  (Groq / Llama / OSS 120B) and Critic Agent (OpenAI / GPT-5.4-mini).
- **Deterministic Lexical Retriever**: Multi-topic query decomposition engine scoring title,
  tag, phrase, and concept matches without vector store drift.
- **Geopolitical Knowledge Bundle (`okf/`)**: 41 structured intelligence concepts across 5 major
  escalation clusters (Hormuz, Taiwan, Gaza, Israel-Lebanon, India-China) with 129 edges.
- **FastAPI Gateway Layer (`api/`)**: REST contracts for `/brief`, `/analyze`, `/compare`,
  `/ready`, `/health`, and `/graph`.
- **Operations Center Frontend (`frontend/`)**: Real-time multi-agent mission dashboard,
  ReactFlow intelligence graph visualizer, and verbatim debate stream.

---

## 2. Graph Composition by Layer & Kind

### By Subsystem Layer
| Layer | Nodes | Description |
|---|---|---|
| `tests` | **352** | Subsystem components for tests |
| `api` | **145** | Subsystem components for api |
| `frontend` | **113** | Subsystem components for frontend |
| `consumer_b` | **91** | Subsystem components for consumer_b |
| `producer` | **89** | Subsystem components for producer |
| `consumer_a` | **80** | Subsystem components for consumer_a |
| `knowledge_bundle` | **42** | Subsystem components for knowledge_bundle |
| `validator` | **41** | Subsystem components for validator |
| `backend` | **21** | Subsystem components for backend |

### By Node Kind
| Kind | Count | Role |
|---|---|---|
| `test` | **229** | Architectural entity (test) |
| `function` | **210** | Architectural entity (function) |
| `module` | **165** | Architectural entity (module) |
| `class` | **150** | Architectural entity (class) |
| `method` | **114** | Architectural entity (method) |
| `component` | **52** | Architectural entity (component) |
| `concept` | **41** | Architectural entity (concept) |
| `endpoint` | **12** | Architectural entity (endpoint) |
| `bundle` | **1** | Architectural entity (bundle) |

---

## 3. High-Centrality Hubs ("God Nodes")

The most connected nodes in the graph serve as primary architectural anchors:

| Rank | Node Label | Kind | Layer | Degree (In / Out) | File Location |
|---|---|---|---|---|---|
| 1 | **OKF Knowledge Catalog** | `bundle` | `knowledge_bundle` | **43** (2 in / 41 out) | `okf:1` |
| 2 | **test_producer.py** | `module` | `tests` | **38** (0 in / 38 out) | `tests/test_producer.py:1` |
| 3 | **test_consumer_b.py** | `module` | `tests` | **37** (0 in / 37 out) | `tests/test_consumer_b.py:1` |
| 4 | **test_consumer_a.py** | `module` | `tests` | **34** (0 in / 34 out) | `tests/test_consumer_a.py:1` |
| 5 | **test_api.py** | `module` | `tests` | **31** (0 in / 31 out) | `tests/test_api.py:1` |
| 6 | **cli.py** | `module` | `producer` | **30** (2 in / 28 out) | `producer/cli.py:1` |
| 7 | **main.py** | `module` | `api` | **27** (3 in / 24 out) | `api/main.py:1` |
| 8 | **service.py** | `module` | `consumer_b` | **27** (4 in / 23 out) | `consumer_b/service.py:1` |
| 9 | **updater.py** | `module` | `producer` | **24** (2 in / 22 out) | `producer/updater.py:1` |
| 10 | **models.py** | `module` | `consumer_b` | **24** (8 in / 16 out) | `consumer_b/models.py:1` |
| 11 | **service.py** | `module` | `consumer_a` | **23** (4 in / 19 out) | `consumer_a/service.py:1` |
| 12 | **reader.py** | `module` | `consumer_a` | **22** (4 in / 18 out) | `consumer_a/reader.py:1` |
| 13 | **rules.py** | `module` | `validator` | **21** (1 in / 20 out) | `validator/rules.py:1` |
| 14 | **models.py** | `module` | `consumer_a` | **21** (8 in / 13 out) | `consumer_a/models.py:1` |
| 15 | **agent-workspace.tsx** | `module` | `frontend` | **21** (0 in / 21 out) | `frontend/components/agent-workspace.tsx:1` |

---

## 4. Key Subsystem Pipelines

### A. Two-Agent Query-Answering Pipeline
```
User Query ──► /api/v1/brief & /api/v1/analyze
                 │                     │
                 ▼                     ▼
     ConsumerService.answer()   ConsumerService.analyze()
                 │                     │
                 └────────► ◄──────────┘
                            │
               detect_topics(query) >= 2?
             ┌──────────────┴──────────────┐
             ▼                             ▼
   Multi-Theatre Scoring         Single-Pass Lexical
   (Hormuz, Taiwan, LAC, etc.)   (Title, Tag, Phrase)
             │                             │
             └──────────────┬──────────────┘
                            ▼
              41-Concept OKF Bundle Catalog
                            │
                            ▼
           Top-N Verified Concepts Retrieved
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
     Groq Llama/OSS-120B          OpenAI GPT-5.4-mini
     (Briefing Synthesis)         (Critical Analysis)
             │                             │
             └──────────────┬──────────────┘
                            ▼
               Operations Center UI Dashboard
                - Briefing Assessment Panel
                - Critical Evaluation Panel
                - Verbatim AI Debate Stream
                - 41-Node Highlighted Graph
```

### B. Geopolitical Knowledge Bundle Clusters
1. **Iran / Strait of Hormuz**: `strait-of-hormuz-maritime-tensions`,
   `hormuz-oil-transit-chokepoint`, `irgc-navy-gulf-posture`
2. **China / Taiwan**: `taiwan-strait-military-tensions`,
   `taiwan-semiconductor-global-supply-chain`, `china-taiwan-reunification-policy`
3. **Gaza / Israel**: `gaza-humanitarian-crisis-infrastructure`,
   `gaza-military-operations-security`, `us-diplomatic-involvement-gaza`
4. **Israel / Hezbollah / Lebanon**: `israel-lebanon-border-conflict`,
   `hezbollah-military-arsenal-posture`, `unscr-1701-disarmament-framework`
5. **India / China**: `india-china-lac-eastern-sector`,
   `arunachal-pradesh-territorial-dispute`, `india-border-infrastructure-development`
6. **Broader Context**: `nato`, `red-sea-shipping-disruptions`, `us-china-tariff-escalation-2026`

---

## 5. Knowledge Graph Artifacts

- **Machine-Readable Graph**: [`.graphify/graph.json`](file://.graphify/graph.json)
- **Interactive Visualizer**: [`.graphify/graph.html`](file://.graphify/graph.html)
- **Manifest & Metadata**: [`.graphify/manifest.json`](file://.graphify/manifest.json)
- **Generator Script**: [`.graphify/generate.py`](file://.graphify/generate.py)
