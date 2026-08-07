"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Columns2, MessageSquareQuote } from "lucide-react";
import { AgentEmptyState } from "@/components/agent-empty-state";
import { AgentWorkspace, type WorkspaceMode } from "@/components/agent-workspace";
import { QuestionForm, type QuestionParams } from "@/components/question-form";
import { TopNav } from "@/components/top-nav";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const [params, setParams] = useState<QuestionParams | null>(null);
  const [mode, setMode] = useState<WorkspaceMode>("agents");

  const activeLoading = false; // loading is handled inside the workspace queries

  return (
    <div className="lab-grid min-h-screen bg-background">
      <TopNav />
      <main className="mx-auto max-w-7xl space-y-6 px-4 pb-20 pt-8">
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
          {/* Mode switch: agents vs debate */}
          <div
            role="tablist"
            aria-label="View mode"
            className="glass inline-flex shrink-0 items-center gap-1 rounded-full border p-1"
          >
            <Button
              size="sm"
              variant="ghost"
              disabled={!params}
              onClick={() => setMode("agents")}
              className={cn(
                "h-7 rounded-full px-3 text-xs",
                mode === "agents" && "bg-secondary font-semibold"
              )}
            >
              <Columns2 className="size-3.5" /> Agents
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={!params}
              onClick={() => setMode("debate")}
              className={cn(
                "h-7 rounded-full px-3 text-xs",
                mode === "debate" && "bg-secondary font-semibold"
              )}
            >
              <MessageSquareQuote className="size-3.5" /> Debate
            </Button>
          </div>
        </div>

        <div className="glass rounded-2xl border p-4">
          <QuestionForm loading={activeLoading} onSubmit={setParams} />
        </div>

        <AnimatePresence mode="popLayout" initial={false}>
          {params ? (
            <motion.div
              key="workspace"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <AgentWorkspace params={params} mode={mode} />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="py-8"
            >
              <AgentEmptyState />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
