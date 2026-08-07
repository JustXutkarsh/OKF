"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { useEffect, useState } from "react";

// Staged agent lifecycle.
//
// The backend does not stream, so progress must be derived honestly from
// the query's real status machine (idle → working → done/error). While a
// query is *pending* we cycle a small set of fixed stage labels —
// descriptive states, not percentages, not fake completion. When the
// query settles, the state snaps to its true terminal immediately.

export type AgentPhase = "idle" | "working" | "debating" | "done" | "error";

/** Statuses surfaced to the user (state indicators + ops log). */
export type AgentStatus =
  | "idle"
  | "searching"
  | "analyzing"
  | "writing"
  | "debating"
  | "completed"
  | "error";

// Segment mapping: the first stage is retrieval ("searching"), the middle
// stages cross-examine ("analyzing"), the tail composes ("writing"). The
// mapping is deterministic and descriptive — never false precision.
const SEARCHING_LAST = 0;
const ANALYZING_LAST = 2;

export function deriveStatus(lifecycle: {
  phase: AgentPhase;
  stageIndex: number;
}): AgentStatus {
  switch (lifecycle.phase) {
    case "idle":
      return "idle";
    case "debating":
      return "debating";
    case "done":
      return "completed";
    case "error":
      return "error";
    case "working": {
      const i = lifecycle.stageIndex;
      if (i <= SEARCHING_LAST) return "searching";
      if (i <= ANALYZING_LAST) return "analyzing";
      return "writing";
    }
  }
}

export interface AgentLifecycle {
  phase: AgentPhase;
  /** Index into `stages` shown as the current activity (working only). */
  stageIndex: number;
  stages: string[];
}

// How long each working-stage label is shown before cycling to the next.
// Rotates through all but the final "waiting" label repeatedly; never
// claims completion until the query actually resolves.
const STAGE_INTERVAL_MS = 2_400;

export function useAgentLifecycle(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  query: UseQueryResult<any>,
  enabled: boolean,
  stages: string[]
): AgentLifecycle {
  const [stageIndex, setStageIndex] = useState(0);

  const working = enabled && query.isPending;

  useEffect(() => {
    if (!working) {
      setStageIndex(0);
      return;
    }
    const id = window.setInterval(() => {
      setStageIndex((i) => (i + 1) % Math.max(stages.length, 1));
    }, STAGE_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [working, stages.length]);

  if (!enabled) return { phase: "idle", stageIndex: 0, stages };
  if (query.isError) return { phase: "error", stageIndex: 0, stages };
  if (query.isPending) return { phase: "working", stageIndex, stages };
  return { phase: "done", stageIndex: 0, stages };
}
