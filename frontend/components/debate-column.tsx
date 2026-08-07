"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { api } from "@/lib/api";
import type { QuestionParams } from "@/components/question-form";
import { DebateStream } from "@/components/debate-stream";
import { Scorecard } from "@/components/scorecard";
import { buildScorecard } from "@/lib/scorecard";

/**
 * Right-hand column: scorecard + debate stream. Reads the agent queries'
 * data from the shared React Query cache (same keys as the ops center, so
 * no duplicate backend calls).
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
      <div className="glass flex h-full min-h-[240px] flex-col items-center justify-center rounded-2xl border p-6 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          Debate stream
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Agents are still investigating — the debate begins once both reports are in.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-[480px] flex-col gap-4">
      {scorecard && <Scorecard data={scorecard} />}
      <div className="min-h-0 flex-1">
        <DebateStream briefing={brief.data} analysis={analyze.data} />
      </div>
    </div>
  );
}
