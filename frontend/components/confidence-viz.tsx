"use client";

import { motion } from "framer-motion";
import type { Briefing } from "@/lib/types";

type Evidence = Briefing["evidence"][number];

const CONFIDENCES = ["verified", "mixed", "unverified"] as const;

const COLOR: Record<(typeof CONFIDENCES)[number], string> = {
  verified: "hsl(164 86% 42%)",
  mixed: "hsl(43 94% 48%)",
  unverified: "hsl(0 72% 51%)",
};

export interface ConfidenceProfile {
  verified: number;
  mixed: number;
  unverified: number;
}

/** Tally evidence-confidence values (case-insensitive) for visualization. */
export function confidenceProfile(evidence: Evidence[]): ConfidenceProfile {
  const profile: ConfidenceProfile = { verified: 0, mixed: 0, unverified: 0 };
  for (const e of evidence) {
    const key = (e.confidence || "").toLowerCase() as keyof ConfidenceProfile;
    if (key in profile) profile[key]++;
  }
  return profile;
}

/**
 * Segmented confidence bar: verified / mixed / unverified proportions across
 * the evidence set. Data-driven, pure visualization, no scoring invented.
 */
export function ConfidenceViz({ evidence }: { evidence: Evidence[] }) {
  const profile = confidenceProfile(evidence);
  const total = evidence.length;
  if (total === 0) {
    return <p className="text-xs text-muted-foreground">no evidence to grade</p>;
  }

  return (
    <div aria-label="confidence breakdown" className="space-y-2">
      <div className="flex h-2.5 gap-px overflow-hidden rounded-full bg-muted">
        {CONFIDENCES.map((key) => {
          const share = profile[key] / total;
          if (share === 0) return null;
          return (
            <motion.div
              key={key}
              initial={{ flexGrow: 0 }}
              animate={{ flexGrow: profile[key] }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="h-full"
              style={{
                backgroundColor: COLOR[key],
                flexBasis: `${share * 100}%`,
                width: `${share * 100}%`,
              }}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-0.5 font-mono text-[10px] text-muted-foreground">
        {CONFIDENCES.map((key) => (
          <span key={key} className="flex items-center gap-1.5">
            <span
              className="inline-block size-1.5 rounded-full"
              style={{ backgroundColor: COLOR[key] }}
            />
            {key} <span className="text-foreground/80">{profile[key]}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
