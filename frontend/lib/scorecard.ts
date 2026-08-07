import type { Analysis, Briefing } from "@/lib/types";

// Intelligence scorecard metrics — every number derives strictly from the
// two real responses, with the computation visible for inspection.
// No arbitrary invented scoring: metrics are fractional rates + a recency delta.

export interface Scorecard {
  /** verified evidence fraction (0-1) across both agents combined;
   * "mixed" counts 0.5, "unverified" 0. */
  confidence: number;
  /** mean matching_score across all evidence, normalized 0-1 by clamping
   * to the observed range (matching_score already is a 0-1 score). */
  evidenceQuality: number;
  /** fraction of BOTH agents' document sets that overlap (paper-agreement proxy). */
  sourceAgreement: number;
  /** days since the latest source access date (lower = fresher). */
  freshnessDays: number;
  /** Raw inputs for inspection: never hidden. */
  details: {
    briefEvidence: number;
    analyzeEvidence: number;
    sharedDocuments: string[];
    totalDocuments: number;
    latestAccessDate: string | null;
  };
}

function setOf(list: string[] | undefined): Set<string> {
  return new Set(list ?? []);
}

export function buildScorecard(brief: Briefing, analysis: Analysis): Scorecard {
  const allEvidence = [...brief.evidence, ...analysis.evidence];
  const verified = allEvidence.filter((e) => e.confidence === "verified").length;
  const mixed = allEvidence.filter((e) => e.confidence === "mixed").length;
  const confidence = allEvidence.length
    ? (verified + mixed * 0.5) / allEvidence.length
    : 0;

  const scores = allEvidence
    .map((e) => e.matching_score)
    .filter((s) => typeof s === "number" && Number.isFinite(s));
  const evidenceQuality = scores.length
    ? scores.reduce((a, b) => a + b, 0) / scores.length
    : 0;

  const briefDocs = setOf(brief.documents_used);
  const analyzeDocs = setOf(analysis.documents_used);
  const shared = [...briefDocs].filter((d) => analyzeDocs.has(d));
  const totalDocs = new Set([...briefDocs, ...analyzeDocs]).size;
  const sourceAgreement = totalDocs > 0 ? shared.length / totalDocs : 0;

  // Freshness: latest accessed date among all sources, in days from today.
  const dates = [...brief.sources, ...analysis.sources]
    .map((s) => s.accessed_date)
    .filter((d): d is string => !!d && !Number.isNaN(Date.parse(d)));
  const latestMs = dates.length ? Math.max(...dates.map((d) => Date.parse(d))) : null;
  const freshnessDays =
    latestMs === null ? -1 : Math.max(0, Math.round((Date.now() - latestMs) / 86_400_000));

  return {
    confidence,
    evidenceQuality,
    sourceAgreement,
    freshnessDays,
    details: {
      briefEvidence: brief.evidence.length,
      analyzeEvidence: analysis.evidence.length,
      sharedDocuments: shared,
      totalDocuments: totalDocs,
      latestAccessDate: latestMs === null ? null : new Date(latestMs).toISOString().slice(0, 10),
    },
  };
}
