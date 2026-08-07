"use client";

import { motion } from "framer-motion";
import { BarChart3 } from "lucide-react";
import type { Scorecard as ScorecardData } from "@/lib/scorecard";

function pct(value: number): number {
  return Math.max(0, Math.min(1, value));
}

/**
 * Intelligence scorecard: four bars derived from real response data
 * (confidence / evidence quality / source agreement / freshness),
 * with exact values and formula-visible tooltips. Freshness uses a
 * recency index where 1.0 = accessed today, decaying linearly to 0 at 30d.
 */
export function Scorecard({ data }: { data: ScorecardData }) {
  const recency = data.freshnessDays < 0 ? 0 : Math.max(0, 1 - data.freshnessDays / 30);

  const rows = [
    {
      label: "confidence",
      value: data.confidence,
      display: `${Math.round(data.confidence * 100)}%`,
      hint: `${data.details.briefEvidence} brief + ${data.details.analyzeEvidence} critic evidence`,
    },
    {
      label: "evidence quality",
      value: data.evidenceQuality,
      display: `${Math.round(data.evidenceQuality * 100)}%`,
      hint: `mean matching_score of all retrieved fragments`,
    },
    {
      label: "source agreement",
      value: data.sourceAgreement,
      display:
        data.details.totalDocuments > 0
          ? `${Math.round(data.sourceAgreement * 100)}%`
          : "n/a",
      hint: `${data.details.sharedDocuments.length}/${data.details.totalDocuments} documents shared`,
    },
    {
      label: "freshness",
      value: recency,
      display:
        data.freshnessDays < 0
          ? "unknown"
          : data.freshnessDays === 0
            ? "today"
            : `${data.freshnessDays}d ago`,
      hint: data.details.latestAccessDate ? `latest source access ${data.details.latestAccessDate}` : "no known access date",
    },
  ];

  return (
    <div className="glass rounded-xl border p-3">
      <p className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        <BarChart3 className="size-3.5" />
        Intelligence scorecard
      </p>
      <div className="space-y-2.5">
        {rows.map((row, i) => (
          <div key={row.label} className="space-y-1">
            <div className="flex items-baseline justify-between text-[11px]">
              <span className="font-mono uppercase tracking-wide text-muted-foreground">
                {row.label}
              </span>
              <span className="font-mono text-foreground">{row.display}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted" title={row.hint}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct(row.value) * 100}%` }}
                transition={{ duration: 0.7, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                className="h-full rounded-full bg-gradient-to-r from-emerald-500/80 to-emerald-400/40"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
