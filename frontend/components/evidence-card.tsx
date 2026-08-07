"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { ConfidenceBadge } from "@/components/evidence-list";
import type { Briefing } from "@/lib/types";

export type Evidence = Briefing["evidence"][number];

/**
 * Expandable evidence card: collapsed shows doc + confidence; click reveals
 * the full diagnostic row (section, matching score, linked source when the
 * caller passes one). This is the evidence-first hero of each agent panel.
 */
export function EvidenceCard({
  evidence,
  source,
}: {
  evidence: Evidence;
  source?: Briefing["sources"][number];
}) {
  const [open, setOpen] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setOpen((o) => !o)}
      aria-expanded={open}
      className="block w-full rounded-lg border bg-background/40 p-3 text-left transition-colors hover:bg-background/70"
    >
      <div className="flex items-center gap-3">
        <span className="min-w-0 flex-1">
          <span className="block truncate font-mono text-xs font-medium">
            {evidence.document_id}
          </span>
          <span className="block truncate text-xs text-muted-foreground">
            {evidence.section}
          </span>
        </span>
        <ConfidenceBadge confidence={evidence.confidence} />
        <span className="font-mono text-[10px] text-muted-foreground">
          {evidence.matching_score.toFixed(2)}
        </span>
        <ChevronDown
          className={`size-3.5 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
        />
      </div>
      {open && (
        <div className="mt-3 space-y-1 border-t pt-3 text-xs text-muted-foreground">
          <p>
            section: <span className="text-foreground/80">{evidence.section}</span>
          </p>
          <p>matching score: {evidence.matching_score}</p>
          {source && (
            <p className="truncate">
              source:{" "}
              <a
                href={source.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-foreground/80 underline underline-offset-2 hover:text-foreground"
                onClick={(e) => e.stopPropagation()}
              >
                {source.source_title}
              </a>
            </p>
          )}
        </div>
      )}
    </button>
  );
}

/** Gallery of evidence cards that appear before the final answer. */
export function EvidenceGallery({
  evidence,
  sources,
}: {
  evidence: Evidence[];
  sources: Briefing["sources"];
}) {
  if (evidence.length === 0) {
    return <p className="text-muted-foreground">No evidence listed.</p>;
  }
  const byDoc = new Map(sources.map((s) => [s.document_id, s]));
  return (
    <div className="grid gap-2">
      {evidence.map((item, i) => (
        <EvidenceCard
          key={`${item.document_id}-${i}`}
          evidence={item}
          source={byDoc.get(item.document_id)}
        />
      ))}
    </div>
  );
}
