"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AgentEmptyState } from "@/components/agent-empty-state";
import { AgentOpsCenter } from "@/components/agent-workspace";
import { DebateColumn } from "@/components/debate-column";
import { KnowledgeGraphPanel } from "@/components/knowledge-graph-panel";
import { QuestionForm, type QuestionParams } from "@/components/question-form";
import { TopNav } from "@/components/top-nav";

export default function HomePage() {
  const [params, setParams] = useState<QuestionParams | null>(null);

  const activeLoading = false; // loading is handled inside the workspace queries

  return (
    <div className="lab-grid min-h-screen bg-background">
      <TopNav />
      <main className="mx-auto max-w-[1500px] space-y-6 px-4 pb-16 pt-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
              OKF · Intelligence Exchange
            </p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">
              Multi-Agent Geopolitical Intelligence
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Two independent AI analysts work the same auditable knowledge bundle in parallel,
              then report against each other.
            </p>
          </div>
        </div>

        <div className="glass rounded-2xl border p-4">
          <QuestionForm loading={activeLoading} onSubmit={setParams} />
        </div>

        <AnimatePresence mode="popLayout" initial={false}>
          {params ? (
            <motion.div
              key="ops"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_360px]"
            >
              {/* Column 1: knowledge graph */}
              <KnowledgeGraphPanel />

              {/* Column 2: agent operations center */}
              <AgentOpsCenter params={params} />

              {/* Column 3: debate stream */}
              <DebateColumn params={params} />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_360px]"
            >
              <KnowledgeGraphPanel />
              <div className="py-8">
                <AgentEmptyState />
              </div>
              <div className="glass flex min-h-[240px] flex-col items-center justify-center rounded-2xl border p-6 text-center">
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Debate stream
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Once both agents report, the exchange replays here — verbatim from
                  each agent's own output.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
