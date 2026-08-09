"use client";

import type { ReactNode } from "react";

export function MetaFooter({
  provider,
  model,
  generatedAt,
  documentsUsed,
  extra,
}: {
  provider: string;
  model: string;
  generatedAt: string;
  documentsUsed: string[];
  extra?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border/40 bg-muted/10 px-3.5 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/50 shrink-0">
          PROVENANCE:
        </span>
        <span className="rounded border border-border/50 bg-muted/30 px-2 py-0.5 font-mono text-[10px] text-muted-foreground/70">
          {provider} · {model}
        </span>

        {documentsUsed.map((id, idx) => (
          <span
            key={`${id}-${idx}`}
            className="rounded border border-border/40 bg-card/60 px-2 py-0.5 font-mono text-[9px] text-muted-foreground/50"
          >
            {id}
          </span>
        ))}

        {extra}

        <span className="ml-auto font-mono text-[9px] text-muted-foreground/40">
          {new Date(generatedAt).toLocaleString()}
        </span>
      </div>
    </div>
  );
}

export function ProvenanceStrip({
  briefing,
  analysis,
}: {
  briefing?: { provider: string; model: string; generated_at: string };
  analysis?: { provider: string; model: string; generated_at: string };
}) {
  if (!briefing && !analysis) return null;

  return (
    <div className="terminal-window rounded-xl p-3 font-mono text-[10px] space-y-2">
      <p className="uppercase tracking-[0.25em] text-muted-foreground/50 text-[9px]">
        GENERATION PROVENANCE METADATA
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {briefing && (
          <div className="flex items-center justify-between rounded border border-border/40 bg-card/40 px-3 py-2">
            <span className="text-emerald-400 font-semibold">BRIEFING-01</span>
            <span className="text-muted-foreground/70">
              {briefing.provider} · {briefing.model}
            </span>
            <span className="text-muted-foreground/40">
              {new Date(briefing.generated_at).toLocaleTimeString()}
            </span>
          </div>
        )}
        {analysis && (
          <div className="flex items-center justify-between rounded border border-border/40 bg-card/40 px-3 py-2">
            <span className="text-amber-400 font-semibold">CRITIC-02</span>
            <span className="text-muted-foreground/70">
              {analysis.provider} · {analysis.model}
            </span>
            <span className="text-muted-foreground/40">
              {new Date(analysis.generated_at).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
