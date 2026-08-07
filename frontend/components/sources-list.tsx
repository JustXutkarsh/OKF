import { ExternalLink } from "lucide-react";
import type { Briefing } from "@/lib/types";

type Source = Briefing["sources"][number];

export function SourcesList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return <p className="text-muted-foreground">No sources listed.</p>;
  return (
    <div className="space-y-2 text-sm">
      {sources.map((source, index) => (
        <div key={index} className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-medium">{source.source_title}</p>
            <p className="truncate text-xs text-muted-foreground">
              {source.document_title} ({source.document_id}) · accessed {source.accessed_date}
            </p>
          </div>
          <a
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            className="mt-0.5 shrink-0 text-muted-foreground transition-colors hover:text-foreground"
            aria-label={`Open source: ${source.source_title}`}
          >
            <ExternalLink className="size-4" />
          </a>
        </div>
      ))}
    </div>
  );
}
