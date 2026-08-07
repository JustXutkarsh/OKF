import type { Analysis, Briefing } from "@/lib/types";

export interface DebateMessage {
  author: "briefing" | "critic";
  kind: "statement" | "question" | "challenge";
  /** Verbatim excerpt of the agents' outputs this message cites. */
  text: string;
  /** True when the critic claims/the statement and critic diverge. */
  disagreement?: boolean;
  detail?: string;
}

/**
 * Structured message sequence built from the two real reports. Content is
 * verbatim excerpts of backend outputs only — never invented. The debate
 * *narrates* what the agents have already produced; it does not synthesize
 * new content.
 */
export function buildDebateMessages(briefing: Briefing, analysis: Analysis): DebateMessage[] {
  const critic = analysis.critical_analysis;
  const messages: DebateMessage[] = [];

  // Round 1: what is happening
  messages.push({
    author: "briefing",
    kind: "statement",
    text: briefing.answer.current_situation,
    detail: `Current situation · ${briefing.evidence.length} evidence`,
  });
  messages.push({
    author: "critic",
    kind: "question",
    text: critic.confidence_assessment,
    detail: "Confidence assessment",
    disagreement: !critic.confidence_assessment.startsWith("This topic is not covered"),
  });

  // Round 2: what is claimed
  if (briefing.answer.key_developments.length) {
    messages.push({
      author: "briefing",
      kind: "statement",
      text:
        "Key developments: " +
        briefing.answer.key_developments.slice(0, 3).join(" · "),
      detail: `${briefing.answer.key_developments.length} developments`,
    });
  }
  if (critic.assumptions.length) {
    messages.push({
      author: "critic",
      kind: "challenge",
      text: "Underlying assumptions: " + critic.assumptions.slice(0, 3).join(" · "),
      detail: `${critic.assumptions.length} assumptions`,
      disagreement: true,
    });
  }

  // Round 3: what is uncertain / missing
  if (critic.conflicting_evidence.length) {
    messages.push({
      author: "critic",
      kind: "challenge",
      text:
        "Verifiable conflict: " +
        critic.conflicting_evidence.map((c) => c.description).join(" · "),
      detail: `${critic.conflicting_evidence.length} conflict(s)`,
      disagreement: true,
    });
  }
  if (critic.missing_information.length) {
    messages.push({
      author: "critic",
      kind: "challenge",
      text: "Missing information: " + critic.missing_information.join(" · "),
      detail: `${critic.missing_information.length} gap(s)`,
      disagreement: true,
    });
  }
  if (critic.alternative_interpretations.length) {
    messages.push({
      author: "critic",
      kind: "statement",
      text:
        "Alternative interpretations: " +
        critic.alternative_interpretations.slice(0, 2).join(" · "),
      detail: `${critic.alternative_interpretations.length} alternative(s)`,
      disagreement: false,
    });
  }

  return messages;
}
