"use client";

import { useQuery } from "@tanstack/react-query";
import { RadarIcon, ScaleIcon } from "lucide-react";
import { api } from "@/lib/api";
import { deriveStatus, useAgentLifecycle } from "@/lib/agent-lifecycle";
import { useOpsTrace } from "@/lib/ops-trace";
import type { QuestionParams } from "@/components/question-form";
import { AgentPanel, type AgentIdentity } from "@/components/agent-panel";
import { AnalysisContent } from "@/components/analysis-view";
import { BriefingContent } from "@/components/briefing-view";
import { DebateView } from "@/components/debate-view";
import { OpsLog } from "@/components/ops-log";
import { ErrorBoundary } from "@/components/error-boundary";
import { ErrorCard } from "@/components/section-card";

export const BRIEFING_AGENT: AgentIdentity = {
  callsign: "AGENT://BRIEFING-01",
  title: "Briefing Agent",
  role: "Synthesizes grounded situation reports from retrieved documents.",
  Icon: RadarIcon,
  color: "var(--agent-brief)",
  phases: [
    "Searching knowledge base…",
    "Retrieving documents…",
    "Evaluating evidence…",
    "Constructing response…",
    "Validating sources…",
  ],
};

export const ANALYSIS_AGENT: AgentIdentity = {
  callsign: "AGENT://CRITIC-02",
  title: "Critical Analysis Agent",
  role: "Challenges assumptions and surfaces uncertainty in the briefing.",
  Icon: ScaleIcon,
  color: "var(--agent-analysis)",
  phases: [
    "Scanning retrieved documents…",
    "Searching for assumptions…",
    "Cross-examining evidence…",
    "Identifying information gaps…",
    "Assessing confidence…",
  ],
};

export type WorkspaceMode = "agents" | "debate";

/** The two-agent workspace: single source of queries, split into two panels. */
export function AgentWorkspace({
  params,
  mode,
}: {
  params: QuestionParams;
  mode: WorkspaceMode;
}) {
  const brief = useQuery({
    queryKey: ["brief", params.question, params.maxDocs],
    queryFn: () => api.brief(params.question, params.maxDocs),
  });
  const analyze = useQuery({
    queryKey: ["analyze", params.question, params.maxDocs],
    queryFn: () => api.analyze(params.question, params.maxDocs),
  });

  const briefLife = useAgentLifecycle(brief, true, BRIEFING_AGENT.phases);
  const analyzeLife = useAgentLifecycle(analyze, true, ANALYSIS_AGENT.phases);

  // Live ops trace: one line per real agent state transition.
  const events = useOpsTrace(
    [
      { agent: BRIEFING_AGENT.title, query: brief, lifecycle: briefLife },
      { agent: ANALYSIS_AGENT.title, query: analyze, lifecycle: analyzeLife },
    ],
    true
  );

  const bothDone = brief.isSuccess && analyze.isSuccess;

  return (
    <div className="space-y-4">
      <OpsLog events={events} />

      {mode === "debate" && bothDone ? (
        <DebateView briefing={brief.data} analysis={analyze.data} />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          <AgentPanel agent={BRIEFING_AGENT} lifecycle={briefLife}>
            {brief.isError && <ErrorCard error={brief.error} />}
            {brief.isSuccess && (
              <ErrorBoundary scope="Briefing" route="/brief">
                <BriefingContent data={brief.data} />
              </ErrorBoundary>
            )}
          </AgentPanel>

          <AgentPanel agent={ANALYSIS_AGENT} lifecycle={analyzeLife}>
            {analyze.isError && <ErrorCard error={analyze.error} />}
            {analyze.isSuccess && (
              <ErrorBoundary scope="Critical analysis" route="/analyze">
                <AnalysisContent data={analyze.data} />
              </ErrorBoundary>
            )}
          </AgentPanel>
        </div>
      )}
    </div>
  );
}

// Re-export for existing consumers (tests keep extending this).
export { deriveStatus };
