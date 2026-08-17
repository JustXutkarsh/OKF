// Knowledge graph construction from the OKF bundle (pure, testable).
//
// The bundle lives next to the frontend at `../okf` (monorepo layout); the
// API route `app/api/graph/route.ts` calls this module to expose a clean
// nodes/edges JSON shape the client fetches once. Parsing never mutates
// anything, and files that can't be parsed yield an error node note so the
// UI stays honest about partial data.

import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

export interface GraphNode {
  id: string;
  title: string;
  /** Concept type: concept | actor | place | source | etc. */
  type: string;
  resource?: string;
  confidence?: string;
  /** True when the document failed frontmatter parsing. */
  parseError?: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface KnowledgeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  errors: string[];
}

/** Extract YAML frontmatter from a markdown OKF document without a parser. */
function frontmatterOf(content: string): Record<string, unknown> | null {
  if (!content.startsWith("---")) return null;
  const end = content.indexOf("\n---", 3);
  if (end === -1) return null;
  const yaml = content.slice(3, end).trim();
  try {
    // Minimal flat-key extraction sufficient for OKF frontmatter keys.
    const out: Record<string, unknown> = {};
    for (const line of yaml.split(/\r?\n/)) {
      const idx = line.indexOf(":");
      if (idx === -1) continue;
      const key = line.slice(0, idx).trim();
      let value: unknown = line.slice(idx + 1).trim().replace(/^["']|["']$/g, "");
      if (typeof value === "string" && value.startsWith("[") && value.endsWith("]")) {
        value = value
          .slice(1, -1)
          .split(",")
          .map((v) => v.trim().replace(/^["']|["']$/g, ""))
          .filter(Boolean);
      }
      out[key] = value;
    }
    return out;
  } catch {
    return null;
  }
}

/** Build nodes+edges from in-memory documents (100% pure for testing). */
export function buildGraph(
  documents: Iterable<{ path: string; content: string }>
): KnowledgeGraph {
  const nodes: GraphNode[] = [];
  const edgePairs: GraphEdge[] = [];
  const errors: string[] = [];
  const idSet = new Set<string>();

  for (const { path, content } of documents) {
    const fm = frontmatterOf(content);
    if (!fm || typeof fm.id !== "string" || !fm.id) {
      errors.push(`${path}: missing/invalid frontmatter (no id)`);
      continue;
    }
    const node: GraphNode = {
      id: fm.id,
      title: typeof fm.title === "string" ? fm.title : fm.id,
      type: typeof fm.type === "string" ? fm.type : "unknown",
      resource: typeof fm.resource === "string" ? fm.resource : undefined,
      confidence: typeof fm.confidence === "string" ? fm.confidence : undefined,
    };
    nodes.push(node);
    idSet.add(node.id);
    if (Array.isArray(fm.related)) {
      for (const rel of fm.related) {
        if (typeof rel === "string" && rel) {
          edgePairs.push({ id: `${fm.id}->${rel}`, source: fm.id, target: rel });
        }
      }
    }
  }
  // Keep only edges whose both endpoints exist — honest about dangling links.
  const edges = edgePairs.filter((e) => idSet.has(e.source) && idSet.has(e.target));
  return { nodes, edges, errors };
}

import bundleGraphData from "./bundle-graph.json";

/** Server-side bundle scan. Never throws; falls back to bundled concept graph if filesystem is absent. */
export function loadBundleGraph(bundlePath?: string): KnowledgeGraph {
  if (bundlePath) {
    const root = resolve(bundlePath);
    if (!existsSync(root)) return { nodes: [], edges: [], errors: [`bundle not found at ${root}`] };
    const docs: { path: string; content: string }[] = [];
    const walk = (dir: string) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.isFile() && entry.name.endsWith(".md")) {
          docs.push({ path: full, content: readFileSync(full, "utf-8") });
        }
      }
    };
    try {
      walk(root);
    } catch (err) {
      return { nodes: [], edges: [], errors: [`bundle read failed: ${String(err)}`] };
    }
    return buildGraph(docs);
  }

  // Auto-discover bundle root from known candidate paths
  const candidates = [
    process.env.OKF_BUNDLE_PATH,
    join(process.cwd(), "..", "okf"),
    join(process.cwd(), "okf"),
  ].filter(Boolean) as string[];

  for (const candidate of candidates) {
    const root = resolve(candidate);
    if (existsSync(root)) {
      const docs: { path: string; content: string }[] = [];
      const walk = (dir: string) => {
        for (const entry of readdirSync(dir, { withFileTypes: true })) {
          const full = join(dir, entry.name);
          if (entry.isDirectory()) walk(full);
          else if (entry.isFile() && entry.name.endsWith(".md")) {
            docs.push({ path: full, content: readFileSync(full, "utf-8") });
          }
        }
      };
      try {
        walk(root);
        const graph = buildGraph(docs);
        if (graph.nodes.length > 0) return graph;
      } catch {
        // Fall through to next candidate or fallback
      }
    }
  }

  // Serverless / Vercel fallback: return the validated bundle knowledge graph
  return bundleGraphData as KnowledgeGraph;
}
