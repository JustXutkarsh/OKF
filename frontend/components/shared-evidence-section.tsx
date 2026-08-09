"use client";

import { EvidenceGallery } from "@/components/evidence-card";
import type { Briefing, Analysis } from "@/lib/types";

export function SharedEvidenceSection({
  briefing,
  analysis,
}: {
  briefing?: Briefing;
  analysis?: Analysis;
}) {
  if (!briefing && !analysis) return null;

  // Combine unique evidence fragments from both agents
  const allEvidence = briefing?.evidence || analysis?.evidence || [];
  const allSources = briefing?.sources || analysis?.sources || [];

  return (
    <section id="section-evidence" className="scroll-mt-20 space-y-3">
      {/* Chapter Header */}
      <div className="flex items-center justify-between border-b border-border/50 pb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-cyan-400">03</span>
          <span className="font-mono text-xs text-muted-foreground/40">/</span>
          <h2 className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-foreground">
            SHARED EVIDENCE
          </h2>
          <span className="ml-2 font-mono text-[10px] text-muted-foreground/50">
            — Evidence retrieved and shared by both agents
          </span>
        </div>
        <span className="font-mono text-[10px] text-muted-foreground/50">
          {allEvidence.length} FRAGMENTS RETRIEVED
        </span>
      </div>

      {/* Shared Evidence Card Container */}
      <div className="terminal-window rounded-xl p-4">
        {allEvidence.length === 0 ? (
          <p className="font-mono text-[11px] text-muted-foreground/50">No evidence available.</p>
        ) : (
          <EvidenceGallery evidence={allEvidence} sources={allSources} />
        )}
      </div>
    </section>
  );
}
