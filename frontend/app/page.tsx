"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AgentEmptyState } from "@/components/agent-empty-state";
import { AgentPanel, BRIEFING_AGENT, ANALYSIS_AGENT } from "@/components/agent-panel";
import { BriefingContent } from "@/components/briefing-view";
import { AnalysisContent } from "@/components/analysis-view";
import { DebateStream } from "@/components/debate-stream";
import { KnowledgeGraphPanel } from "@/components/knowledge-graph-panel";
import { MissionTimeline } from "@/components/mission-timeline";
import { QuestionForm, type QuestionParams } from "@/components/question-form";
import { Scorecard } from "@/components/scorecard";
import { SectionNav } from "@/components/section-nav";
import { SharedEvidenceSection } from "@/components/shared-evidence-section";
import { SourcesList } from "@/components/sources-list";
import { ProvenanceStrip } from "@/components/meta-footer";
import { TopNav } from "@/components/top-nav";
import { ErrorBoundary } from "@/components/error-boundary";
import { ErrorCard } from "@/components/section-card";
import { api } from "@/lib/api";
import { useAgentLifecycle } from "@/lib/agent-lifecycle";
import { useOpsTrace } from "@/lib/ops-trace";
import { buildScorecard } from "@/lib/scorecard";

function MissionResults({ params }: { params: QuestionParams }) {
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

  const isWorking = briefLife.phase === "working" || analyzeLife.phase === "working";
  const ready = brief.isSuccess && analyze.isSuccess;
  const scorecard = ready ? buildScorecard(brief.data, analyze.data) : null;

  return (
    <div className="space-y-12">
      {/* ── Active Execution view during working phase ── */}
      {isWorking && (
        <section id="section-execution" className="scroll-mt-20 space-y-3">
          <div className="flex items-center gap-2 border-b border-border/50 pb-2">
            <span className="font-mono text-xs font-bold text-cyan-400">02</span>
            <span className="font-mono text-xs text-muted-foreground/40">/</span>
            <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
              AGENT EXECUTION
            </h2>
            <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
              — Agents processing mission in real time
            </span>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_280px]">
            <AgentPanel agent={BRIEFING_AGENT} lifecycle={briefLife} reportData={brief.data} />
            <AgentPanel agent={ANALYSIS_AGENT} lifecycle={analyzeLife} reportData={analyze.data} />
            <MissionTimeline events={events} />
          </div>
        </section>
      )}

      {/* ── 04 / INTELLIGENCE ASSESSMENT (Primary Focal Point) ── */}
      <section id="section-results" className="scroll-mt-20 space-y-4">
        <div className="flex items-center justify-between border-b border-border/50 pb-2">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-cyan-400">04</span>
            <span className="font-mono text-xs text-muted-foreground/40">/</span>
            <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
              INTELLIGENCE ASSESSMENT
            </h2>
            <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
              — Synthesized Situation Report vs Critical Evaluation Dossier
            </span>
          </div>
          {ready && (
            <span className="font-mono text-[10px] text-emerald-400 uppercase tracking-widest">
              ● ASSESSMENT COMPLETE
            </span>
          )}
        </div>

        {/* Two Balanced Columns */}
        <div className="grid gap-6 lg:grid-cols-2 items-start">
          {/* Left Column: BRIEFING ASSESSMENT */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-border/30 pb-2">
              <span className="font-mono text-[11px] font-bold text-emerald-400 tracking-wider">
                BRIEFING ASSESSMENT
              </span>
              <span className="font-mono text-[9px] text-muted-foreground/50">
                {brief.data ? `${brief.data.provider} / ${brief.data.model}` : "STANDBY"}
              </span>
            </div>
            {brief.isPending && (
              <div className="terminal-window rounded-xl p-6 text-center">
                <p className="font-mono text-xs text-muted-foreground/50">
                  Briefing synthesis in progress…
                </p>
              </div>
            )}
            {brief.isError && <ErrorCard error={brief.error} />}
            {brief.isSuccess && (
              <ErrorBoundary scope="Briefing" route="/brief">
                <BriefingContent data={brief.data} />
              </ErrorBoundary>
            )}
          </div>

          {/* Right Column: CRITICAL ASSESSMENT */}
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-border/30 pb-2">
              <span className="font-mono text-[11px] font-bold text-amber-400 tracking-wider">
                CRITICAL ASSESSMENT
              </span>
              <span className="font-mono text-[9px] text-muted-foreground/50">
                {analyze.data ? `${analyze.data.provider} / ${analyze.data.model}` : "STANDBY"}
              </span>
            </div>
            {analyze.isPending && (
              <div className="terminal-window rounded-xl p-6 text-center">
                <p className="font-mono text-xs text-muted-foreground/50">
                  Critical evaluation in progress…
                </p>
              </div>
            )}
            {analyze.isError && <ErrorCard error={analyze.error} />}
            {analyze.isSuccess && (
              <ErrorBoundary scope="Critical analysis" route="/analyze">
                <AnalysisContent data={analyze.data} />
              </ErrorBoundary>
            )}
          </div>
        </div>
      </section>

      {/* ── 05 / AI DEBATE ROOM ── */}
      <section id="section-debate" className="scroll-mt-20 space-y-3">
        <div className="flex items-center gap-2 border-b border-border/50 pb-2">
          <span className="font-mono text-xs font-bold text-cyan-400">05</span>
          <span className="font-mono text-xs text-muted-foreground/40">/</span>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
            AI DEBATE ROOM
          </h2>
          <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
            — Independent conclusions compared against each other
          </span>
        </div>

        {ready ? (
          <DebateStream briefing={brief.data} analysis={analyze.data} />
        ) : (
          <div className="terminal-window rounded-xl p-8 text-center font-mono text-[11px] text-muted-foreground/40">
            Awaiting completion of both agents to initiate debate stream…
          </div>
        )}
      </section>

      {/* ── 06 / CONFIDENCE & ASSESSMENT ── */}
      <section id="section-confidence" className="scroll-mt-20 space-y-3">
        <div className="flex items-center gap-2 border-b border-border/50 pb-2">
          <span className="font-mono text-xs font-bold text-cyan-400">06</span>
          <span className="font-mono text-xs text-muted-foreground/40">/</span>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
            CONFIDENCE & ASSESSMENT
          </h2>
          <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
            — Quantitative intelligence quality metrics
          </span>
        </div>

        {scorecard ? (
          <Scorecard data={scorecard} />
        ) : (
          <div className="terminal-window rounded-xl p-6 text-center font-mono text-[11px] text-muted-foreground/40">
            Metrics calculated once assessment completes…
          </div>
        )}
      </section>

      {/* ── 07 / SOURCES & PROVENANCE ── */}
      <section id="section-sources" className="scroll-mt-20 space-y-4">
        <div className="flex items-center gap-2 border-b border-border/50 pb-2">
          <span className="font-mono text-xs font-bold text-cyan-400">07</span>
          <span className="font-mono text-xs text-muted-foreground/40">/</span>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
            SOURCES & PROVENANCE
          </h2>
          <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
            — Primary documentation references and generation lineage
          </span>
        </div>

        <div className="terminal-window rounded-xl p-4 space-y-4">
          <div>
            <p className="mb-3 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/50">
              PRIMARY SOURCES
            </p>
            <SourcesList sources={brief.data?.sources || analyze.data?.sources || []} />
          </div>

          <ProvenanceStrip briefing={brief.data} analysis={analyze.data} />
        </div>
      </section>

      {/* ── 03 / SHARED EVIDENCE ── */}
      <SharedEvidenceSection briefing={brief.data} analysis={analyze.data} />

      {/* ── 02 / AGENT EXECUTION (Historical Execution Summary) ── */}
      {!isWorking && (
        <section id="section-execution" className="scroll-mt-20 space-y-3">
          <div className="flex items-center gap-2 border-b border-border/50 pb-2">
            <span className="font-mono text-xs font-bold text-cyan-400">02</span>
            <span className="font-mono text-xs text-muted-foreground/40">/</span>
            <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
              EXECUTION HISTORY
            </h2>
            <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
              — Execution logs and compact agent status
            </span>
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_280px]">
            <AgentPanel agent={BRIEFING_AGENT} lifecycle={briefLife} reportData={brief.data} />
            <AgentPanel agent={ANALYSIS_AGENT} lifecycle={analyzeLife} reportData={analyze.data} />
            <MissionTimeline events={events} />
          </div>
        </section>
      )}

      {/* ── 08 / INTELLIGENCE NETWORK ── */}
      <section id="section-network" className="scroll-mt-20 space-y-3">
        <div className="flex items-center gap-2 border-b border-border/50 pb-2">
          <span className="font-mono text-xs font-bold text-cyan-400">08</span>
          <span className="font-mono text-xs text-muted-foreground/40">/</span>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
            INTELLIGENCE NETWORK
          </h2>
          <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
            — Concept relationships mapped across knowledge bundle
          </span>
        </div>

        <KnowledgeGraphPanel />
      </section>
    </div>
  );
}

export default function HomePage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useState<QuestionParams | null>(null);
  const [missionFlash, setMissionFlash] = useState(false);

  function handleSubmit(p: QuestionParams) {
    setParams(p);
    setMissionFlash(true);
    setTimeout(() => setMissionFlash(false), 1200);
    queryClient.invalidateQueries({ queryKey: ["ready"] });
    queryClient.invalidateQueries({ queryKey: ["version"] });
  }

  return (
    <div className="ops-grid min-h-screen bg-background text-foreground font-mono">
      {/* Global Top Nav */}
      <TopNav />

      {/* Chapter 01: Mission Control */}
      <div className="mx-auto max-w-[1600px] px-6 pt-4 space-y-4">
        <section id="section-mission" className="scroll-mt-20">
          <div className="terminal-window rounded-xl border border-border/50">
            <div className="flex items-center gap-3 border-b border-border/40 px-4 py-2.5">
              <div className="flex gap-1.5">
                <span className="status-dot bg-red-500/60" />
                <span className="status-dot bg-yellow-500/40" />
                <span className="status-dot bg-green-500/40" />
              </div>
              <span className="font-mono text-xs font-bold text-cyan-400">01</span>
              <span className="font-mono text-xs text-muted-foreground/40">/</span>
              <h1 className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground/70">
                MISSION CONTROL
              </h1>
              <AnimatePresence>
                {missionFlash && (
                  <motion.span
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 ml-auto"
                  >
                    ▸ MISSION DISPATCHED
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
            <div className="p-4">
              <QuestionForm loading={false} onSubmit={handleSubmit} />
            </div>
          </div>
        </section>
      </div>

      {/* Sticky Section Navigator */}
      <SectionNav />

      {/* Workstation Body */}
      <main className="mx-auto max-w-[1600px] px-6 py-6">
        <AnimatePresence mode="popLayout" initial={false}>
          {params ? (
            <motion.div
              key="active-mission"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
            >
              <MissionResults params={params} />
            </motion.div>
          ) : (
            <motion.div
              key="idle-standby"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-8"
            >
              <section id="section-execution">
                <AgentEmptyState />
              </section>

              <section id="section-network" className="space-y-3">
                <div className="flex items-center gap-2 border-b border-border/50 pb-2">
                  <span className="font-mono text-xs font-bold text-cyan-400">08</span>
                  <span className="font-mono text-xs text-muted-foreground/40">/</span>
                  <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
                    INTELLIGENCE NETWORK
                  </h2>
                </div>
                <KnowledgeGraphPanel />
              </section>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
