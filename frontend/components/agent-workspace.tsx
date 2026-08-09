"use client";

import { useQuery } from "@tanstack/react-query";
import { RadarIcon, ScaleIcon } from "lucide-react";
import { api } from "@/lib/api";
import { useAgentLifecycle } from "@/lib/agent-lifecycle";
import { useOpsTrace } from "@/lib/ops-trace";
import type { QuestionParams } from "@/components/question-form";
import { AgentPanel, type AgentIdentity } from "@/components/agent-panel";
import { AnalysisContent } from "@/components/analysis-view";
import { BriefingContent } from "@/components/briefing-view";
import { EvidenceRadar } from "@/components/evidence-radar";
import { MissionTimeline } from "@/components/mission-timeline";
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
    "Identifying assumptions…",
    "Cross-examining evidence…",
    "Identifying information gaps…",
    "Assessing confidence…",
  ],
};

/** Agent operations center: two agent terminals + mission timeline sidebar. */
export function AgentOpsCenter({ params }: { params: QuestionParams }) {
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

  const events = useOpsTrace(
    [
      { agent: BRIEFING_AGENT.title, query: brief, lifecycle: briefLife },
      { agent: ANALYSIS_AGENT.title, query: analyze, lifecycle: analyzeLife },
    ],
    true
  );

  const briefActive = briefLife.phase === "working";
  const analyzeActive = analyzeLife.phase === "working";

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_220px]">
      {/* Agent BRIEFING-01 terminal */}
      <AgentPanel agent={BRIEFING_AGENT} lifecycle={briefLife}>
        {brief.isError && <ErrorCard error={brief.error} />}
        {brief.isSuccess && (
          <>
            <div className="mb-4 rounded-lg border border-border/40 bg-background/30 p-3">
              <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/50">
                EVIDENCE RADAR
              </p>
              <EvidenceRadar active={briefActive} documents={brief.data.documents_used} />
            </div>
            <ErrorBoundary scope="Briefing" route="/brief">
              <BriefingContent data={brief.data} />
            </ErrorBoundary>
          </>
        )}
      </AgentPanel>

      {/* Agent CRITIC-02 terminal */}
      <AgentPanel agent={ANALYSIS_AGENT} lifecycle={analyzeLife}>
        {analyze.isError && <ErrorCard error={analyze.error} />}
        {analyze.isSuccess && (
          <>
            <div className="mb-4 rounded-lg border border-border/40 bg-background/30 p-3">
              <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/50">
                EVIDENCE RADAR
              </p>
              <EvidenceRadar active={analyzeActive} documents={analyze.data.documents_used} />
            </div>
            <ErrorBoundary scope="Critical analysis" route="/analyze">
              <AnalysisContent data={analyze.data} />
            </ErrorBoundary>
          </>
        )}
      </AgentPanel>

      {/* Mission timeline sidebar */}
      <MissionTimeline events={events} />
    </div>
  );
}
