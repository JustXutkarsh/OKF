"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import type { QuestionParams } from "@/components/question-form";
import { DebateStream } from "@/components/debate-stream";
import { Scorecard } from "@/components/scorecard";
import { buildScorecard } from "@/lib/scorecard";

/**
 * Debate column: intel confidence metrics + AI Debate Room.
 * Reads from the shared React Query cache — no duplicate calls.
 */
export function DebateColumn({ params }: { params: QuestionParams }) {
  const brief = useQuery({
    queryKey: ["brief", params.question, params.maxDocs],
    queryFn: () => api.brief(params.question, params.maxDocs),
  });
  const analyze = useQuery({
    queryKey: ["analyze", params.question, params.maxDocs],
    queryFn: () => api.analyze(params.question, params.maxDocs),
  });

  const ready = brief.isSuccess && analyze.isSuccess;
  const scorecard = useMemo(
    () => (ready ? buildScorecard(brief.data, analyze.data) : null),
    [ready, brief.data, analyze.data]
  );

  if (!ready) {
    return (
      <div className="terminal-window flex min-h-[280px] flex-col items-center justify-center rounded-xl p-6 text-center">
        <motion.div
          animate={{ opacity: [0.3, 0.8, 0.3] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="mb-3 font-mono text-[9px] uppercase tracking-[0.35em] text-muted-foreground/40"
        >
          AI DEBATE ROOM
        </motion.div>
        <p className="font-mono text-[11px] text-muted-foreground/40">
          Debate begins once both agents complete.
        </p>
        <div className="mt-4 flex gap-2">
          <span
            className="status-dot animate-signal-pulse"
            style={{ backgroundColor: "hsl(var(--agent-brief) / 0.6)" }}
          />
          <span
            className="status-dot animate-signal-pulse"
            style={{
              backgroundColor: "hsl(var(--agent-analysis) / 0.6)",
              animationDelay: "0.3s",
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {scorecard && <Scorecard data={scorecard} />}
      <div className="min-h-0 flex-1">
        <DebateStream briefing={brief.data} analysis={analyze.data} />
      </div>
    </div>
  );
}
