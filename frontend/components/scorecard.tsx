"use client";

import { motion } from "framer-motion";
import type { Scorecard as ScorecardData } from "@/lib/scorecard";

function pct(value: number): number {
  return Math.max(0, Math.min(1, value));
}

const METRIC_COLORS = [
  "hsl(var(--terminal-green))",
  "hsl(var(--terminal-cyan))",
  "hsl(var(--agent-brief))",
  "hsl(var(--terminal-amber))",
];

/**
 * Intelligence confidence metrics panel — formatted cleanly for the workstation.
 * Correctly formats Evidence Quality (e.g. 9.0 / 10 or 90%, never 900%).
 */
export function Scorecard({ data }: { data: ScorecardData }) {
  const recency = data.freshnessDays < 0 ? 0 : Math.max(0, 1 - data.freshnessDays / 30);

  // Raw evidence quality is mean matching_score (can be on 0-1 scale or 0-10 scale depending on bundle).
  // If > 1, normalized to 0-1 scale for progress bar, displayed as "9.0 / 10" or "90%".
  const normEq = data.evidenceQuality > 1 ? data.evidenceQuality / 10 : data.evidenceQuality;
  const displayEq =
    data.evidenceQuality > 1
      ? `${data.evidenceQuality.toFixed(1)} / 10`
      : `${Math.round(data.evidenceQuality * 100)}%`;

  const rows = [
    {
      label: "CONFIDENCE",
      value: data.confidence,
      display: `${Math.round(data.confidence * 100)}%`,
      hint: `${data.details.briefEvidence} brief + ${data.details.analyzeEvidence} critic evidence`,
    },
    {
      label: "EVIDENCE QUALITY",
      value: normEq,
      display: displayEq,
      hint: "mean matching_score of all retrieved fragments",
    },
    {
      label: "SOURCE AGREEMENT",
      value: data.sourceAgreement,
      display:
        data.details.totalDocuments > 0
          ? `${Math.round(data.sourceAgreement * 100)}%`
          : "N/A",
      hint: `${data.details.sharedDocuments.length}/${data.details.totalDocuments} documents shared`,
    },
    {
      label: "FRESHNESS",
      value: recency,
      display:
        data.freshnessDays < 0
          ? "UNKNOWN"
          : data.freshnessDays === 0
            ? "TODAY"
            : `${data.freshnessDays}D AGO`,
      hint: data.details.latestAccessDate
        ? `latest access ${data.details.latestAccessDate}`
        : "no known access date",
    },
  ];

  return (
    <div className="terminal-window rounded-xl p-4">
      <div className="mb-4 flex items-center justify-between border-b border-border/40 pb-2.5">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/70">
          INTEL CONFIDENCE METRICS
        </p>
        <span className="font-mono text-[9px] text-muted-foreground/40">
          {data.details.briefEvidence + data.details.analyzeEvidence} FRAGMENTS EVALUATED
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {rows.map((row, i) => (
          <div
            key={row.label}
            className="rounded-lg border border-border/40 bg-card/40 p-3"
            title={row.hint}
          >
            <span className="block font-mono text-[9px] uppercase tracking-widest text-muted-foreground/60 mb-1">
              {row.label}
            </span>
            <span
              className="block font-mono text-xl font-bold tabular-nums"
              style={{ color: METRIC_COLORS[i] }}
            >
              {row.display}
            </span>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted/40">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct(row.value) * 100}%` }}
                transition={{ duration: 0.8, delay: i * 0.1, ease: [0.22, 1, 0.36, 1] }}
                className="h-full rounded-full"
                style={{ backgroundColor: METRIC_COLORS[i] }}
              />
            </div>
            <span className="mt-1.5 block font-mono text-[9px] text-muted-foreground/40 truncate">
              {row.hint}
            </span>
          </div>
        ))}
      </div>

      {/* Shared docs tag */}
      {data.details.sharedDocuments.length > 0 && (
        <div className="mt-4 border-t border-border/30 pt-3 flex items-center gap-2">
          <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/50 shrink-0">
            SHARED DOCUMENTS:
          </span>
          <div className="flex flex-wrap gap-1">
            {data.details.sharedDocuments.map((doc, idx) => (
              <span
                key={`${doc}-${idx}`}
                className="rounded border border-border/40 bg-muted/30 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground/70"
              >
                {doc}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
