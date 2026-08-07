import { Badge } from "@/components/ui/badge";
import type { Briefing } from "@/lib/types";

type Evidence = Briefing["evidence"][number];

const CONFIDENCE_VARIANT = {
  verified: "success",
  mixed: "warning",
  unverified: "destructive",
} as const;

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const variant =
    CONFIDENCE_VARIANT[confidence as keyof typeof CONFIDENCE_VARIANT] ?? "secondary";
  return <Badge variant={variant}>{confidence || "unknown"}</Badge>;
}

export function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) return <p className="text-muted-foreground">No evidence listed.</p>;
  return (
    <div className="divide-y text-sm">
      {evidence.map((item, index) => (
        <div key={index} className="flex items-center justify-between gap-3 py-2">
          <div className="min-w-0">
            <span className="font-mono text-xs">{item.document_id}</span>
            <span className="mx-2 text-muted-foreground">·</span>
            <span className="text-muted-foreground">{item.section}</span>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-xs text-muted-foreground">score {item.matching_score}</span>
            <ConfidenceBadge confidence={item.confidence} />
          </div>
        </div>
      ))}
    </div>
  );
}
