#!/usr/bin/env python3
"""
OKF Codebase & Intelligence Knowledge Graph Generator (.graphify)

Parses Python ASTs, TypeScript/TSX components and routes, Markdown OKF bundle concepts,
FastAPI endpoints, and test suites to produce:
  - .graphify/graph.json (Structured knowledge graph)
  - .graphify/graph.html (Interactive standalone force-directed graph visualizer)
  - .graphify/GRAPH_REPORT.md (Architectural analysis & god node report)
  - .graphify/manifest.json (Metadata & entry points)
"""

from __future__ import annotations

import ast
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPHIFY_DIR = REPO_ROOT / ".graphify"


class CodebaseGraphBuilder:
    def __init__(self, root: Path):
        self.root = root
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._edge_set: set[tuple[str, str, str]] = set()

    def add_node(
        self,
        node_id: str,
        label: str,
        kind: str,
        layer: str,
        file_path: str,
        line: int = 1,
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if node_id in self.nodes:
            # Update summary/metadata if richer
            if summary and not self.nodes[node_id].get("summary"):
                self.nodes[node_id]["summary"] = summary
            if metadata:
                self.nodes[node_id]["metadata"].update(metadata)
            return

        self.nodes[node_id] = {
            "id": node_id,
            "label": label,
            "kind": kind,
            "layer": layer,
            "file": file_path,
            "line": line,
            "summary": summary,
            "metadata": metadata or {},
        }

    def add_edge(
        self,
        source: str,
        target: str,
        kind: str,
        label: str = "",
        weight: float = 1.0,
    ) -> None:
        if not source or not target or source == target:
            return
        edge_key = (source, target, kind)
        if edge_key in self._edge_set:
            return
        self._edge_set.add(edge_key)
        self.edges.append(
            {
                "source": source,
                "target": target,
                "kind": kind,
                "label": label or kind,
                "weight": weight,
            }
        )

    def process_python_file(self, file_path: Path) -> None:
        rel_path = str(file_path.relative_to(self.root))

        # Determine layer
        layer = "backend"
        if rel_path.startswith("consumer_a"):
            layer = "consumer_a"
        elif rel_path.startswith("consumer_b"):
            layer = "consumer_b"
        elif rel_path.startswith("api"):
            layer = "api"
        elif rel_path.startswith("producer"):
            layer = "producer"
        elif rel_path.startswith("validator"):
            layer = "validator"
        elif rel_path.startswith("tests"):
            layer = "tests"
        elif rel_path.startswith("config"):
            layer = "config"

        module_name = rel_path.replace("/", ".").replace(".py", "")
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]

        mod_node_id = f"py:mod:{module_name}"

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return

        docstring = ast.get_docstring(tree) or f"Python module {module_name}"
        self.add_node(
            node_id=mod_node_id,
            label=f"{file_path.name}",
            kind="module",
            layer=layer,
            file_path=rel_path,
            line=1,
            summary=docstring.strip().split("\n")[0],
            metadata={"module": module_name},
        )

        for node in tree.body:
            # Classes
            if isinstance(node, ast.ClassDef):
                cls_id = f"py:cls:{module_name}.{node.name}"
                cls_doc = ast.get_docstring(node) or f"Class {node.name}"
                self.add_node(
                    node_id=cls_id,
                    label=node.name,
                    kind="class",
                    layer=layer,
                    file_path=rel_path,
                    line=node.lineno,
                    summary=cls_doc.strip().split("\n")[0],
                    metadata={"bases": [ast.unparse(b) for b in node.bases]},
                )
                self.add_edge(mod_node_id, cls_id, "defines")

                for base in node.bases:
                    base_name = ast.unparse(base)
                    # Link common base classes
                    for other_id in self.nodes:
                        if other_id.endswith(f".{base_name}"):
                            self.add_edge(cls_id, other_id, "inherits_from")

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        meth_id = f"py:fn:{module_name}.{node.name}.{item.name}"
                        meth_doc = ast.get_docstring(item) or f"Method {item.name}"
                        self.add_node(
                            node_id=meth_id,
                            label=f"{node.name}.{item.name}()",
                            kind="method" if not item.name.startswith("test_") else "test",
                            layer=layer,
                            file_path=rel_path,
                            line=item.lineno,
                            summary=meth_doc.strip().split("\n")[0],
                            metadata={"args": [a.arg for a in item.args.args]},
                        )
                        self.add_edge(cls_id, meth_id, "defines")

            # Top-level Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_id = f"py:fn:{module_name}.{node.name}"
                fn_doc = ast.get_docstring(node) or f"Function {node.name}"
                kind = "test" if node.name.startswith("test_") else "function"

                # Check for FastAPI route decorators
                is_route = False
                http_method = "GET"
                route_path = ""
                for dec in node.decorator_list:
                    dec_str = ast.unparse(dec)
                    for m in ["get", "post", "put", "delete", "patch"]:
                        if f".{m}(" in dec_str or dec_str.startswith(f"{m}("):
                            is_route = True
                            http_method = m.upper()
                            # Extract path string
                            if (
                                isinstance(dec, ast.Call)
                                and dec.args
                                and isinstance(dec.args[0], ast.Constant)
                            ):
                                route_path = dec.args[0].value
                            break

                if is_route:
                    endpoint_id = f"api:{http_method}:{route_path or node.name}"
                    self.add_node(
                        node_id=endpoint_id,
                        label=f"{http_method} {route_path or '/' + node.name}",
                        kind="endpoint",
                        layer="api",
                        file_path=rel_path,
                        line=node.lineno,
                        summary=fn_doc.strip().split("\n")[0],
                        metadata={"method": http_method, "path": route_path, "handler": node.name},
                    )
                    self.add_edge(mod_node_id, endpoint_id, "routes_to")
                    self.add_edge(endpoint_id, fn_id, "handled_by")

                self.add_node(
                    node_id=fn_id,
                    label=f"{node.name}()",
                    kind=kind,
                    layer=layer,
                    file_path=rel_path,
                    line=node.lineno,
                    summary=fn_doc.strip().split("\n")[0],
                    metadata={"args": [a.arg for a in node.args.args]},
                )
                self.add_edge(mod_node_id, fn_id, "defines")

            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target_mod = f"py:mod:{alias.name}"
                    self.add_edge(mod_node_id, target_mod, "imports")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    target_mod = f"py:mod:{node.module}"
                    self.add_edge(mod_node_id, target_mod, "imports")
                    for alias in node.names:
                        target_entity = f"py:cls:{node.module}.{alias.name}"
                        self.add_edge(mod_node_id, target_entity, "imports")

    def process_okf_bundle(self) -> None:
        okf_dir = self.root / "okf"
        if not okf_dir.exists():
            return

        bundle_mod_id = "bundle:okf_catalog"
        self.add_node(
            node_id=bundle_mod_id,
            label="OKF Knowledge Catalog",
            kind="bundle",
            layer="knowledge_bundle",
            file_path="okf",
            line=1,
            summary=(
                "Geopolitical Intelligence Bundle with 41 structured concepts "
                "and 129 relationship edges"
            ),
            metadata={
                "version": 1,
                "theatres": [
                    "Hormuz",
                    "Taiwan",
                    "Gaza",
                    "Israel-Lebanon",
                    "India-China",
                    "NATO",
                    "Red Sea",
                ],
            },
        )

        for md_file in okf_dir.glob("**/*.md"):
            rel_path = str(md_file.relative_to(self.root))
            content = md_file.read_text(encoding="utf-8")

            # Extract frontmatter
            if not content.startswith("---"):
                continue
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            frontmatter_raw = parts[1]
            body = parts[2]

            # Simple YAML parser
            doc_id = ""
            title = md_file.stem
            resource = "concept"
            confidence = "verified"
            related: list[str] = []

            for line in frontmatter_raw.splitlines():
                line = line.strip()
                if line.startswith("id:"):
                    doc_id = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("resource:"):
                    resource = line.split(":", 1)[1].strip()
                elif line.startswith("confidence:"):
                    confidence = line.split(":", 1)[1].strip()
                elif line.startswith("related:"):
                    m = re.search(r"\[(.*?)\]", line)
                    if m:
                        related = [
                            r.strip().strip('"').strip("'")
                            for r in m.group(1).split(",")
                            if r.strip()
                        ]

            if not doc_id:
                doc_id = md_file.stem

            # Extract summary
            summary = ""
            sum_match = re.search(r"## Summary\s*\n+([^\n#]+)", body)
            if sum_match:
                summary = sum_match.group(1).strip()

            concept_node_id = f"okf:{doc_id}"
            self.add_node(
                node_id=concept_node_id,
                label=title,
                kind="concept",
                layer="knowledge_bundle",
                file_path=rel_path,
                line=1,
                summary=summary or f"Intelligence concept: {title}",
                metadata={
                    "concept_id": doc_id,
                    "resource": resource,
                    "confidence": confidence,
                    "related_count": len(related),
                },
            )
            self.add_edge(bundle_mod_id, concept_node_id, "contains")

            for rel in related:
                rel_target_id = f"okf:{rel}"
                self.add_edge(concept_node_id, rel_target_id, "related_to")

    def process_frontend_files(self) -> None:
        frontend_dir = self.root / "frontend"
        if not frontend_dir.exists():
            return

        for ext in ["*.ts", "*.tsx"]:
            for file_path in frontend_dir.glob(f"**/{ext}"):
                rel_path = str(file_path.relative_to(self.root))
                if "node_modules" in rel_path or ".next" in rel_path:
                    continue

                layer = "frontend"
                if "tests" in rel_path:
                    layer = "tests"
                elif "components" in rel_path:
                    layer = "frontend"
                elif "app/api" in rel_path:
                    layer = "api"
                elif "lib" in rel_path:
                    layer = "frontend"

                content = file_path.read_text(encoding="utf-8")
                mod_id = f"ts:mod:{rel_path}"

                self.add_node(
                    node_id=mod_id,
                    label=file_path.name,
                    kind="module",
                    layer=layer,
                    file_path=rel_path,
                    line=1,
                    summary=f"Frontend module {file_path.name}",
                    metadata={},
                )

                # Find React components and exported functions
                comp_matches = re.finditer(
                    r"export\s+(?:default\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9_]+)", content
                )
                for m in comp_matches:
                    comp_name = m.group(1)
                    comp_id = f"ts:comp:{comp_name}"
                    self.add_node(
                        node_id=comp_id,
                        label=f"<{comp_name} />",
                        kind="component",
                        layer=layer,
                        file_path=rel_path,
                        line=1,
                        summary=f"React component {comp_name}",
                        metadata={"name": comp_name},
                    )
                    self.add_edge(mod_id, comp_id, "defines")

                # Find test cases
                test_matches = re.finditer(r'(?:it|test)\s*\(\s*["\']([^"\']+)["\']', content)
                for tm in test_matches:
                    test_desc = tm.group(1)
                    test_id = f"ts:test:{file_path.stem}:{test_desc[:30]}"
                    self.add_node(
                        node_id=test_id,
                        label=f"it: {test_desc[:25]}...",
                        kind="test",
                        layer="tests",
                        file_path=rel_path,
                        line=1,
                        summary=f"Vitest case: {test_desc}",
                        metadata={"description": test_desc},
                    )
                    self.add_edge(mod_id, test_id, "defines")

                # Find import links to other components / libs
                import_matches = re.finditer(r'import\s+.*?from\s+["\'](@/[^"\']+)["\']', content)
                for im in import_matches:
                    import_path = im.group(1).replace("@/", "frontend/")
                    # Link to target module
                    for other_id, other_node in self.nodes.items():
                        if (
                            other_node["file"].startswith(import_path)
                            or other_node["file"] == f"{import_path}.ts"
                            or other_node["file"] == f"{import_path}.tsx"
                        ):
                            self.add_edge(mod_id, other_id, "imports")

    def connect_pipeline_and_cross_cutting_edges(self) -> None:
        """Add high-level architectural flows between components, services, and the bundle."""
        # 1. API routers to Consumer services
        self.add_edge(
            "py:fn:api.routers.briefing.post_brief",
            "py:fn:consumer_a.service.ConsumerService.answer",
            "invokes",
        )
        self.add_edge(
            "py:fn:api.routers.analysis.post_analyze",
            "py:fn:consumer_b.service.ConsumerService.analyze",
            "invokes",
        )
        self.add_edge(
            "py:fn:api.routers.compare.post_compare",
            "py:fn:consumer_a.service.ConsumerService.answer",
            "invokes",
        )
        self.add_edge(
            "py:fn:api.routers.compare.post_compare",
            "py:fn:consumer_b.service.ConsumerService.analyze",
            "invokes",
        )
        self.add_edge("api:GET:/api/v1/graph", "bundle:okf_catalog", "exposes_network")

        # 2. Consumers to Retrievers & Readers
        self.add_edge(
            "py:fn:consumer_a.service.ConsumerService.answer",
            "py:fn:consumer_a.retriever.select",
            "retrieves_with",
        )
        self.add_edge(
            "py:fn:consumer_b.service.ConsumerService.analyze",
            "py:fn:consumer_b.retriever.select",
            "retrieves_with",
        )
        self.add_edge(
            "py:fn:consumer_a.retriever.select", "bundle:okf_catalog", "indexes_and_scores"
        )
        self.add_edge(
            "py:fn:consumer_b.retriever.select", "bundle:okf_catalog", "indexes_and_scores"
        )

        # 3. Frontend API client to Backend Endpoints
        self.add_edge("ts:mod:frontend/lib/api.ts", "api:POST:/brief", "calls_endpoint")
        self.add_edge("ts:mod:frontend/lib/api.ts", "api:POST:/analyze", "calls_endpoint")
        self.add_edge("ts:mod:frontend/lib/api.ts", "api:GET:/ready", "calls_endpoint")
        self.add_edge("ts:mod:frontend/lib/api.ts", "api:GET:/version", "calls_endpoint")
        self.add_edge("ts:comp:KnowledgeGraphPanel", "api:GET:/api/v1/graph", "visualizes")

        # 4. Tests to System Under Test
        self.add_edge("py:mod:tests.test_consumer_a", "py:mod:consumer_a.service", "tests")
        self.add_edge("py:mod:tests.test_consumer_b", "py:mod:consumer_b.service", "tests")
        self.add_edge("py:mod:tests.test_api", "py:mod:api.main", "tests")
        self.add_edge("py:mod:tests.test_validator", "py:mod:validator.schema", "tests")

    def build_graph(self) -> dict[str, Any]:
        # Filter edges to ensure endpoints exist
        valid_edges = [
            e for e in self.edges if e["source"] in self.nodes and e["target"] in self.nodes
        ]

        # Calculate degree metrics
        in_degrees: dict[str, int] = {nid: 0 for nid in self.nodes}
        out_degrees: dict[str, int] = {nid: 0 for nid in self.nodes}
        for e in valid_edges:
            out_degrees[e["source"]] = out_degrees.get(e["source"], 0) + 1
            in_degrees[e["target"]] = in_degrees.get(e["target"], 0) + 1

        for nid, node in self.nodes.items():
            node["in_degree"] = in_degrees.get(nid, 0)
            node["out_degree"] = out_degrees.get(nid, 0)
            node["total_degree"] = node["in_degree"] + node["out_degree"]

        # Layer and kind distributions
        layers_count: dict[str, int] = {}
        kinds_count: dict[str, int] = {}
        for node in self.nodes.values():
            layers_count[node["layer"]] = layers_count.get(node["layer"], 0) + 1
            kinds_count[node["kind"]] = kinds_count.get(node["kind"], 0) + 1

        return {
            "version": "1.0.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "repository": "JustXutkarsh/OKF",
            "stats": {
                "nodes_count": len(self.nodes),
                "edges_count": len(valid_edges),
                "layers": layers_count,
                "kinds": kinds_count,
            },
            "nodes": list(self.nodes.values()),
            "edges": valid_edges,
        }


def generate_graph_html(graph_data: dict[str, Any]) -> str:
    """Generates a standalone, dark-themed interactive knowledge graph viewer."""
    graph_json_str = json.dumps(graph_data)
    template_path = GRAPHIFY_DIR / "viewer_template.html"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = (
            "<html><body><script>const data = __GRAPH_DATA_PLACEHOLDER__;</script></body></html>"
        )
    return template.replace("__GRAPH_DATA_PLACEHOLDER__", graph_json_str)


def generate_graph_report_md(graph_data: dict[str, Any]) -> str:
    """Generates GRAPH_REPORT.md summarizing repository topology and god nodes."""
    stats = graph_data["stats"]
    nodes = graph_data["nodes"]

    # Sort nodes by total degree to find God Nodes / Hubs
    sorted_by_degree = sorted(nodes, key=lambda n: n.get("total_degree", 0), reverse=True)
    top_hubs = sorted_by_degree[:15]

    report = f"""# OKF Codebase & Intelligence Architecture Graph Report (.graphify)

**Generated:** {graph_data["generated_at"]}
**Repository:** {graph_data["repository"]}
**Graph Nodes:** {stats["nodes_count"]} | **Graph Edges:** {stats["edges_count"]}

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
"""
    for layer, count in sorted(stats["layers"].items(), key=lambda x: x[1], reverse=True):
        report += f"| `{layer}` | **{count}** | Subsystem components for {layer} |\n"

    report += """
### By Node Kind
| Kind | Count | Role |
|---|---|---|
"""
    for kind, count in sorted(stats["kinds"].items(), key=lambda x: x[1], reverse=True):
        report += f"| `{kind}` | **{count}** | Architectural entity ({kind}) |\n"

    report += """
---

## 3. High-Centrality Hubs ("God Nodes")

The most connected nodes in the graph serve as primary architectural anchors:

| Rank | Node Label | Kind | Layer | Degree (In / Out) | File Location |
|---|---|---|---|---|---|
"""
    for idx, hub in enumerate(top_hubs, 1):
        tot = hub.get("total_degree", 0)
        in_d = hub.get("in_degree", 0)
        out_d = hub.get("out_degree", 0)
        loc = f"{hub['file']}:{hub['line']}"
        report += (
            f"| {idx} | **{hub['label']}** | `{hub['kind']}` | `{hub['layer']}` | "
            f"**{tot}** ({in_d} in / {out_d} out) | `{loc}` |\n"
        )

    report += """
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
"""
    return report


def main() -> None:
    GRAPHIFY_DIR.mkdir(parents=True, exist_ok=True)
    builder = CodebaseGraphBuilder(REPO_ROOT)

    # 1. Parse Python packages
    for py_file in REPO_ROOT.glob("**/*.py"):
        rel = str(py_file.relative_to(REPO_ROOT))
        if any(
            ignored in rel
            for ignored in [
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".graphify",
            ]
        ):
            continue
        builder.process_python_file(py_file)

    # 2. Parse OKF Knowledge Bundle
    builder.process_okf_bundle()

    # 3. Parse Frontend TS/TSX
    builder.process_frontend_files()

    # 4. Connect cross-subsystem edges
    builder.connect_pipeline_and_cross_cutting_edges()

    # 5. Build Graph
    graph_data = builder.build_graph()

    # 6. Write graph.json
    graph_json_path = GRAPHIFY_DIR / "graph.json"
    graph_json_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
    n_nodes = len(graph_data["nodes"])
    n_edges = len(graph_data["edges"])
    print(f"Generated: {graph_json_path} ({n_nodes} nodes, {n_edges} edges)")

    # 7. Write graph.html
    graph_html_path = GRAPHIFY_DIR / "graph.html"
    graph_html_path.write_text(generate_graph_html(graph_data), encoding="utf-8")
    print(f"Generated: {graph_html_path}")

    # 8. Write GRAPH_REPORT.md
    report_md_path = GRAPHIFY_DIR / "GRAPH_REPORT.md"
    report_md_path.write_text(generate_graph_report_md(graph_data), encoding="utf-8")
    print(f"Generated: {report_md_path}")

    # 9. Write manifest.json
    manifest_path = GRAPHIFY_DIR / "manifest.json"
    manifest_data = {
        "name": "OKF Codebase & Intelligence Graph",
        "version": "1.0.0",
        "generated_at": graph_data["generated_at"],
        "files": {
            "graph_json": "graph.json",
            "graph_html": "graph.html",
            "report_md": "GRAPH_REPORT.md",
        },
        "stats": graph_data["stats"],
        "entry_points": [
            {"name": "FastAPI Gateway", "node_id": "py:mod:api.main"},
            {"name": "Briefing Consumer A", "node_id": "py:mod:consumer_a.service"},
            {"name": "Critic Consumer B", "node_id": "py:mod:consumer_b.service"},
            {"name": "OKF Catalog", "node_id": "bundle:okf_catalog"},
            {"name": "Frontend Dashboard", "node_id": "ts:mod:frontend/app/page.tsx"},
        ],
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"Generated: {manifest_path}")


if __name__ == "__main__":
    main()
