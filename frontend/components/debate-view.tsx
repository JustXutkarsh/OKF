"use client";

import { motion } from "framer-motion";
import { RadarIcon, ScaleIcon } from "lucide-react";
import type { Analysis, Briefing } from "@/lib/types";
import { ListSection, SectionCard } from "@/components/section-card";
import { Reveal, StaggerGroup } from "@/components/reveal";

/**
 * Debate mode: the two agents, built from the SAME bundle, argue point by
 * point. Briefing states; Critical Analysis responds. Differences and gaps
 * are highlighted by the critic's accent. Side-by-side summaries are
 * opaque — the interleaved format makes the dialectic legible.
 */
export function DebateView({ briefing, analysis }: { briefing: Briefing; analysis: Analysis }) {
  const critic = analysis.critical_analysis;

  const exchanges: {
    agentSays: { title: string; body: React.ReactNode };
    criticResponds: { title: string; body: React.ReactNode };
  }[] = [
    {
      agentSays: {
        title: "Current situation",
        body: <p className="text-sm leading-relaxed">{briefing.answer.current_situation}</p>,
      },
      criticResponds: {
        title: "Confidence assessment",
        body: <p className="text-sm leading-relaxed">{critic.confidence_assessment}</p>,
      },
    },
    {
      agentSays: {
        title: "Key developments",
        body: <ListSection items={briefing.answer.key_developments} />,
      },
      criticResponds: {
        title: "Assumptions this relies on",
        body: <ListSection items={critic.assumptions} />,
      },
    },
    {
      agentSays: {
        title: "Key actors",
        body: <ListSection items={briefing.answer.key_actors} />,
      },
      criticResponds: {
        title: "Uncertainties",
        body: <ListSection items={critic.uncertainties} />,
      },
    },
  ];

  const playOf = (exchange: (typeof exchanges)[number], index: number) => (
    <div key={index} className="grid gap-3 lg:grid-cols-2">
      {/* Briefing agent statement */}
      <motion.div
        variants={{ hidden: { opacity: 0, x: -16 }, show: { opacity: 1, x: 0 } }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="rounded-xl border p-4"
        style={{
          borderColor: "hsl(var(--agent-brief) / 0.35)",
          backgroundColor: "hsl(var(--agent-brief) / 0.05)",
        }}
      >
        <p className="mb-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
          <RadarIcon className="size-3.5" style={{ color: "hsl(var(--agent-brief))" }} />
          Briefing says · {exchange.agentSays.title}
        </p>
        {exchange.agentSays.body}
      </motion.div>

      {/* Critical analysis response */}
      <motion.div
        variants={{ hidden: { opacity: 0, x: 16 }, show: { opacity: 1, x: 0 } }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
        className="rounded-xl border p-4"
        style={{
          borderColor: "hsl(var(--agent-analysis) / 0.4)",
          backgroundColor: "hsl(var(--agent-analysis) / 0.06)",
        }}
      >
        <p className="mb-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
          <ScaleIcon className="size-3.5" style={{ color: "hsl(var(--agent-analysis))" }} />
          Critic responds · {exchange.criticResponds.title}
        </p>
        {exchange.criticResponds.body}
      </motion.div>
    </div>
  );

  return (
    <StaggerGroup className="space-y-3">
      {exchanges.map(playOf)}

      {/* Divergence surfaced: conflicts + information gaps */}
      <Reveal>
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionCard title="Points of conflict">
            {critic.conflicting_evidence.length === 0 ? (
              <p className="text-muted-foreground">The agents agree on the retrieved documents.</p>
            ) : (
              <ul className="list-disc space-y-1.5 pl-5 text-sm">
                {critic.conflicting_evidence.map((c, i) => (
                  <li key={i}>{c.description}</li>
                ))}
              </ul>
            )}
          </SectionCard>
          <SectionCard title="Information gaps">
            {critic.missing_information.length === 0 ? (
              <p className="text-muted-foreground">No gaps flagged.</p>
            ) : (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                <ListSection items={critic.missing_information} />
              </div>
            )}
          </SectionCard>
        </div>
      </Reveal>
    </StaggerGroup>
  );
}
