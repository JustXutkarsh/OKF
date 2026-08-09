"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useEffect, useState } from "react";
import { motion } from "framer-motion";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
  MarkerType,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { Network } from "lucide-react";
import type { KnowledgeGraph } from "@/lib/knowledge-graph";

// Node type color coding for the command center graph
const TYPE_COLORS: Record<string, string> = {
  concept: "hsl(var(--agent-brief))",
  actor: "hsl(var(--terminal-cyan))",
  place: "hsl(var(--agent-analysis))",
  source: "hsl(var(--terminal-green))",
  event: "hsl(var(--terminal-amber))",
  unknown: "hsl(var(--muted-foreground) / 0.6)",
};

function getTypeColor(type: string): string {
  return TYPE_COLORS[type] ?? TYPE_COLORS.unknown;
}

function layoutGraph(
  graph: KnowledgeGraph,
  isDark: boolean
): { nodes: Node[]; edges: Edge[] } {
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
    const color = getTypeColor(n.type);
    nodes.push({
      id: n.id,
      position: { x, y },
      data: { label: n.title, node: n },
      style: {
        background: isDark ? "hsl(224 45% 9%)" : "hsl(0 0% 100%)",
        border: `1px solid ${color}50`,
        borderRadius: 6,
        fontSize: 10,
        padding: "5px 8px",
        color: isDark ? "hsl(210 40% 85%)" : "hsl(220 40% 15%)",
        maxWidth: 150,
        boxShadow: isDark ? `0 0 12px -4px ${color}40` : "none",
        fontFamily: "var(--font-geist-mono)",
      },
    });
  });

  const edgeColor = isDark ? "hsl(215 20% 40%)" : "hsl(214 32% 75%)";
  const edges: Edge[] = graph.edges.map((e, i) => ({
    id: e.id || `edge-${i}`,
    source: e.source,
    target: e.target,
    style: {
      stroke: edgeColor,
      opacity: 0.6,
      strokeWidth: 1,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 10,
      height: 10,
      color: edgeColor,
    },
  }));

  return { nodes, edges };
}

export function KnowledgeGraphPanel() {
  const [isDark, setIsDark] = useState(false);
  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
    const obs = new MutationObserver(() =>
      setIsDark(document.documentElement.classList.contains("dark"))
    );
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);

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
    return layoutGraph(query.data, isDark);
  }, [query.data, isDark]);

  const [rfNodes, setNodes] = useNodesState([]);
  const [rfEdges, setEdges] = useEdgesState([]);
  useEffect(() => {
    setNodes(nodes);
    setEdges(edges);
  }, [nodes, edges, setNodes, setEdges]);

  // Type legend
  const typeSet = new Set(query.data?.nodes.map((n) => n.type) ?? []);
  const legendTypes = [...typeSet].slice(0, 5);

  return (
    <div className="terminal-window flex h-[400px] flex-col rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border/50 px-3 py-2.5">
        <motion.span
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 3 }}
          className="status-dot"
          style={{ backgroundColor: "hsl(var(--terminal-green))" }}
        />
        <Network className="size-3.5 text-muted-foreground/60" />
        <p className="flex-1 font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          INTELLIGENCE NETWORK
        </p>
        {query.data && (
          <p className="font-mono text-[9px] text-muted-foreground/40">
            {query.data.nodes.length} NODES · {query.data.edges.length} EDGES
          </p>
        )}
      </div>

      {/* Graph */}
      <div className="min-h-0 flex-1 relative">
        {query.isPending && (
          <div className="flex h-full items-center justify-center">
            <motion.p
              animate={{ opacity: [0.4, 0.9, 0.4] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground/40"
            >
              MAPPING CONCEPTS…
            </motion.p>
          </div>
        )}
        {query.isError && (
          <div className="flex h-full items-center justify-center p-4 text-center">
            <p className="font-mono text-[10px] text-muted-foreground/40">
              BUNDLE MAP UNAVAILABLE
            </p>
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
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color={isDark ? "hsl(223 35% 18%)" : "hsl(214 32% 88%)"}
            />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
      </div>

      {/* Type legend */}
      {legendTypes.length > 0 && (
        <div className="flex flex-wrap gap-3 border-t border-border/40 px-3 py-2 bg-muted/10">
          {legendTypes.map((type) => (
            <div key={type} className="flex items-center gap-1.5">
              <span
                className="status-dot"
                style={{ backgroundColor: getTypeColor(type), width: 6, height: 6 }}
              />
              <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/60">
                {type}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
