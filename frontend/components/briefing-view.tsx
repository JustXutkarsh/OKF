"use client";

import type { Briefing } from "@/lib/types";
import { ConfidenceViz } from "@/components/confidence-viz";
import { Reveal, StaggerGroup } from "@/components/reveal";
import { Typewriter } from "@/components/typewriter";
import { DossierSection, IntelItem } from "@/components/dossier-section";

const NOT_COVERED = "This topic is not covered";

export function BriefingContent({ data }: { data: Briefing }) {
  if (data.answer.current_situation.startsWith(NOT_COVERED)) {
    return (
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm">
        <p className="font-mono text-[10px] uppercase tracking-widest text-amber-500/80 mb-2">
          NO COVERAGE
        </p>
        <p className="text-foreground/80">{data.answer.current_situation}</p>
        <p className="mt-2 text-xs text-muted-foreground/60">
          Try a topic covered by the bundle (conflicts, economics, actors, policy).
        </p>
      </div>
    );
  }

  return (
    <StaggerGroup className="space-y-4 max-w-3xl">
      {/* Executive Summary */}
      <Reveal>
        <DossierSection
          title="EXECUTIVE SUMMARY"
          classification="CLASSIFIED"
          accentColor="hsl(var(--agent-brief))"
        >
          <div className="max-w-2xl text-[14px] leading-relaxed text-foreground/90">
            <Typewriter text={data.answer.current_situation} />
          </div>
        </DossierSection>
      </Reveal>

      {/* Key Developments */}
      <Reveal>
        <DossierSection
          title="KEY DEVELOPMENTS"
          accentColor="hsl(var(--agent-brief) / 0.6)"
          action={
            <span className="font-mono text-[10px] text-muted-foreground/40">
              {data.answer.key_developments.length} ITEMS
            </span>
          }
        >
          {data.answer.key_developments.length === 0 ? (
            <p className="text-sm text-muted-foreground/60">None identified.</p>
          ) : (
            <div className="space-y-2.5">
              {data.answer.key_developments.map((item, i) => (
                <IntelItem
                  key={i}
                  index={i}
                  text={item}
                  color="hsl(var(--agent-brief) / 0.6)"
                />
              ))}
            </div>
          )}
        </DossierSection>
      </Reveal>

      {/* Key Actors */}
      <Reveal>
        <DossierSection
          title="KEY ACTORS"
          classification="ACTORS"
          accentColor="hsl(var(--terminal-cyan) / 0.5)"
          action={
            <span className="font-mono text-[10px] text-muted-foreground/40">
              {data.answer.key_actors.length} ENTITIES
            </span>
          }
        >
          {data.answer.key_actors.length === 0 ? (
            <p className="text-sm text-muted-foreground/60">None identified.</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {data.answer.key_actors.map((actor, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 rounded border border-border/40 bg-background/30 px-3 py-2 text-sm text-foreground/90"
                >
                  <span className="shrink-0 font-mono text-[10px] text-cyan-400">▸</span>
                  <span className="font-mono text-xs font-medium">{actor}</span>
                </div>
              ))}
            </div>
          )}
        </DossierSection>
      </Reveal>

      {/* Threat Assessment */}
      <Reveal>
        <DossierSection
          title="THREAT ASSESSMENT"
          classification="RESTRICTED"
          accentColor="hsl(var(--terminal-amber) / 0.5)"
        >
          <ConfidenceViz evidence={data.evidence} />
        </DossierSection>
      </Reveal>
    </StaggerGroup>
  );
}
