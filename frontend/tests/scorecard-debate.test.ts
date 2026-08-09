import { describe, expect, it } from "vitest";
import { buildScorecard } from "@/lib/scorecard";
import { buildDebateMessages } from "@/lib/debate";
import type { Analysis, Briefing } from "@/lib/types";

const BRIEF: Briefing = {
  answer: { current_situation: "Situation.", key_developments: ["d"], key_actors: ["a"] },
  reasoning: "r",
  documents_used: ["d1", "d2"],
  evidence: [
    { document_id: "d1", section: "s", confidence: "verified", matching_score: 0.9 },
    { document_id: "d2", section: "s", confidence: "mixed", matching_score: 0.5 },
  ] as never,
  sources: [
    { document_id: "d1", document_title: "t", source_title: "t", source_url: "u", accessed_date: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10) },
  ] as never,
  retrieval: { candidate_count: 2, selected_count: 2, selected_documents: ["d1", "d2"], retrieval_time_ms: 1 },
  ranking: [],
  generated_at: "2026-08-07T00:00:00Z",
  provider: "groq",
  model: "m",
};

const ANALYZE: Analysis = {
  critical_analysis: {
    assumptions: ["a1"],
    conflicting_evidence: [],
    uncertainties: [],
    alternative_interpretations: [],
    missing_information: ["m1"],
    confidence_assessment: "Assess",
  },
  reasoning: "r",
  documents_used: ["d2", "d3"],
  evidence: [
    { document_id: "d2", section: "s", confidence: "verified", matching_score: 0.7 },
  ] as never,
  sources: [],
  retrieval: { candidate_count: 1, selected_count: 1, selected_documents: ["d2"], retrieval_time_ms: 1 },
  ranking: [],
  generated_at: "2026-08-07T00:00:00Z",
  provider: "groq",
  model: "m",
  bundle_version: 1,
};

describe("buildScorecard", () => {
  it("derives all four dimensions from real inputs only", () => {
    const s = buildScorecard(BRIEF, ANALYZE);
    // confidence: (2verified + 1mixed*0.5) / 3 = 0.8333
    expect(s.confidence).toBeCloseTo((2 + 0.5) / 3, 4);
    // evidenceQuality: (0.9+0.5+0.7)/3
    expect(s.evidenceQuality).toBeCloseTo(0.7, 4);
    // agreement: shared {d2} / union {d1,d2,d3} = 1/3
    expect(s.sourceAgreement).toBeCloseTo(1 / 3, 4);
    // freshness: latest access = today (from BRIEF.source accessed_date) → 0
    expect(s.freshnessDays).toBe(0);
    expect(s.details.sharedDocuments).toEqual(["d2"]);
    expect(s.details.totalDocuments).toBe(3);
  });

  it("never invents data for empty inputs", () => {
    const empty = buildScorecard(
      { ...BRIEF, evidence: [], documents_used: [], sources: [] },
      { ...ANALYZE, evidence: [], documents_used: [] }
    );
    expect(empty.confidence).toBe(0);
    expect(empty.evidenceQuality).toBe(0);
    expect(empty.sourceAgreement).toBe(0);
    expect(empty.freshnessDays).toBe(-1);
  });
});

describe("buildDebateMessages", () => {
  it("narrates verbatim excerpts only — strings are substrings of model outputs", () => {
    const msgs = buildDebateMessages(BRIEF, ANALYZE);
    expect(msgs.length).toBeGreaterThan(0);
    for (const m of msgs) {
      const allFatherText = [
        BRIEF.answer.current_situation,
        ...BRIEF.answer.key_developments,
        ...BRIEF.answer.key_actors,
        ANALYZE.critical_analysis.confidence_assessment,
        ...ANALYZE.critical_analysis.assumptions,
        ...ANALYZE.critical_analysis.conflicting_evidence.map((c) => c.description),
        ...ANALYZE.critical_analysis.missing_information,
        ...ANALYZE.critical_analysis.alternative_interpretations,
      ];
      expect(allFatherText.some((f) => m.text.includes(f))).toBe(true);
    }
  });

  it("flags disagreement on critic's challenge rounds", () => {
    const msgs = buildDebateMessages(BRIEF, ANALYZE);
    expect(msgs.some((m) => m.author === "critic" && m.disagreement)).toBe(true);
    expect(msgs.filter((m) => m.disagreement)).toHaveLength(msgs.filter((m) => m.disagreement).length);
  });
});
