import { describe, expect, it } from "vitest";
import { buildGraph, loadBundleGraph } from "@/lib/knowledge-graph";

const NATO = `---
schema_version: 1
id: nato
type: concept
title: NATO
resource: actors
confidence: verified
related: [ukraine-russia-frontline]
---

## Summary

NATO alliance.`;

const UKRAINE = `---
schema_version: 1
id: ukraine-russia-frontline
type: concept
title: Ukraine-Russia Frontline
resource: conflicts
confidence: mixed
related: [nato, missing-id]
---

## Summary

Frontline.`;

describe("buildGraph", () => {
  it("parses nodes/edges from frontmatter (pure)", () => {
    const g = buildGraph([
      { path: "a/nato.md", content: NATO },
      { path: "c/ukraine.md", content: UKRAINE },
    ]);
    expect(g.nodes).toHaveLength(2);
    expect(g.nodes.map((n) => n.id).sort()).toEqual(["nato", "ukraine-russia-frontline"]);
    // Only edges with both endpoints present are kept (dangling dropped, honestly).
    expect(g.edges.map((e) => e.id).sort()).toEqual([
      "nato->ukraine-russia-frontline",
      "ukraine-russia-frontline->nato",
    ]);
    expect(g.errors).toHaveLength(0);
  });

  it("reports parse errors instead of crashing on malformed docs", () => {
    const g = buildGraph([{ path: "bad.md", content: "no frontmatter here" }]);
    expect(g.nodes).toHaveLength(0);
    expect(g.errors).toHaveLength(1);
    expect(g.errors[0]).toContain("bad.md");
  });

  it("loadBundleGraph returns non-empty graph (> 30 nodes, > 50 edges) for production bundle", () => {
    const g = loadBundleGraph();
    expect(g.nodes.length).toBeGreaterThan(30);
    expect(g.edges.length).toBeGreaterThan(50);
  });

  it("loadBundleGraph returns empty graph with error when explicit invalid path is provided", () => {
    const g = loadBundleGraph("/nonexistent/custom/path");
    expect(g.nodes).toHaveLength(0);
    expect(g.edges).toHaveLength(0);
    expect(g.errors.length).toBeGreaterThan(0);
  });
});
