"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { Network } from "lucide-react";
import type { KnowledgeGraph } from "@/lib/knowledge-graph";

// Simple radial layout: types placed on orbit, resisting graph-lib deps.
function layoutGraph(graph: KnowledgeGraph): { nodes: Node[]; edges: Edge[] } {
  const groups = new Map<string, number>();
  graph.nodes.forEach((n) => {
    if (!groups.has(n.type)) groups.set(n.type, groups.size);
  });
  const byType = [...groups.keys()];
  const center = { x: 240, y: 160 };
  const nodes: Node[] = [];

  const orbitRadius = Math.max(80, graph.nodes.length * 10);
  graph.nodes.forEach((n, i) => {
    const typeIdx = byType.indexOf(n.type);
    const angle = (i / graph.nodes.length) * Math.PI * 2;
    const jitter = (i % 3) * 12;
    const x = center.x + Math.cos(angle) * (orbitRadius + jitter);
    const y = center.y + Math.sin(angle) * (orbitRadius + jitter) + typeIdx * 4;
    nodes.push({
      id: n.id,
      position: { x, y },
      data: { label: n.title, node: n },
      style: {
        background: "hsl(var(--card))",
        border: `1px solid hsl(var(--border))`,
        borderRadius: 8,
        fontSize: 11,
        padding: "6px 8px",
        color: "hsl(var(--foreground))",
        maxWidth: 160,
      },
    });
  });

  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: e.id || `edge-${i}`,
    source: e.source,
    target: e.target,
    style: { stroke: "hsl(var(--muted-foreground))", opacity: 0.5, strokeWidth: 1 },
    markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color: "hsl(var(--muted-foreground))" },
  }));

  return { nodes, edges };
}

export function KnowledgeGraphPanel() {
  const query = useQuery({
    queryKey: ["knowledge-graph"],
    queryFn: async (): Promise<KnowledgeGraph> => {
      const res = await fetch("/api/graph", { cache: "no-store" });
      return res.json();
    },
    staleTime: 30_000,
  });

  const { nodes, edges } = useMemo(() => {
    if (!query.data) return { nodes: [], edges: [] };
    return layoutGraph(query.data);
  }, [query.data]);

  const [rfNodes, setNodes] = useNodesState([]);
  const [rfEdges, setEdges] = useEdgesState([]);
  useEffect(() => {
    setNodes(nodes);
    setEdges(edges);
  }, [nodes, edges, setNodes, setEdges]);

  return (
    <div className="glass flex h-full min-h-[380px] flex-col rounded-2xl border">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Network className="size-4 text-muted-foreground" />
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          Knowledge graph
        </p>
        {query.data && (
          <p className="ml-auto font-mono text-[10px] text-muted-foreground/60">
            {query.data.nodes.length} nodes · {query.data.edges.length} edges
          </p>
        )}
      </div>
      <div className="min-h-0 flex-1">
        {query.isPending && (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            Mapping concepts…
          </div>
        )}
        {query.isError && (
          <div className="p-3 text-xs text-muted-foreground">
            Bundle map unavailable.
          </div>
        )}
        {query.data && (
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            fitView
            nodesDraggable
            nodesConnectable={false}
            zoomOnScroll
            panOnScroll
            proOptions={{ hideAttribution: true }}
            style={{ backgroundColor: "transparent" }}
          >
            <Background gap={24} size={1} color="hsl(var(--border))" />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
        {query.data && query.data.errors.length > 0 && (
          <p className="border-t px-3 py-1 font-mono text-[10px] text-amber-500/80">
            {query.data.errors.length} bundle issue(s)
          </p>
        )}
      </div>
    </div>
  );
}
