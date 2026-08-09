"use client";

import { ExternalLink } from "lucide-react";
import type { Briefing } from "@/lib/types";

type Source = Briefing["sources"][number];

export function SourcesList({ sources }: { sources: Source[] }) {
  if (sources.length === 0)
    return (
      <p className="font-mono text-[10px] text-muted-foreground/50">No sources listed.</p>
    );
  return (
    <div className="space-y-2">
      {sources.map((source, index) => (
        <div
          key={index}
          className="flex items-start justify-between gap-3 rounded border border-border/30 bg-background/30 px-3 py-2"
        >
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground/85">{source.source_title}</p>
            <p className="mt-0.5 font-mono text-[9px] text-muted-foreground/50 truncate">
              {source.document_id} · {source.document_title} · accessed {source.accessed_date}
            </p>
          </div>
          <a
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            className="mt-0.5 shrink-0 text-muted-foreground/40 transition-colors hover:text-foreground"
            aria-label={`Open source: ${source.source_title}`}
          >
            <ExternalLink className="size-3.5" />
          </a>
        </div>
      ))}
    </div>
  );
}
