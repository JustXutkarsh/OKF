"use client";

import { useEffect, useRef, useState } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import {
  deriveStatus,
  type AgentLifecycle,
  type AgentStatus,
} from "@/lib/agent-lifecycle";

// Agent activity log ("ops trace"). Every entry reflects a REAL state
// transition observed from the queries — dispatched, stage transitions,
// completion (with provider/model/docs metadata), or error. Never fake
// events: nothing appears that didn't happen.

export interface OpsEvent {
  /** Monotonic sequence for stable rendering. */
  seq: number;
  /** ISO timestamp when the transition was observed. */
  at: string;
  agent: string;
  status: AgentStatus;
  /** Optional context string (e.g. "200 OK · 3 docs"), never containing content. */
  detail?: string;
}

export interface OpsLogInput {
  agent: string;
  query: UseQueryResult<unknown>;
  lifecycle: AgentLifecycle;
}

export function useOpsTrace(inputs: OpsLogInput[], active: boolean): OpsEvent[] {
  const [events, setEvents] = useState<OpsEvent[]>([]);
  const lastStatusRef = useRef<Record<string, AgentStatus>>({});
  const seqRef = useRef(0);

  useEffect(() => {
    // Reset when there's no live question.
    if (!active) {
      setEvents([]);
      lastStatusRef.current = {};
      return;
    }
  }, [active]);

  useEffect(() => {
    if (!active) return;
    const fresh: OpsEvent[] = [];
    for (const input of inputs) {
      const status = deriveStatus(input.lifecycle);
      const last = lastStatusRef.current[input.agent];
      if (status === last) continue;
      lastStatusRef.current[input.agent] = status;

      let detail: string | undefined;
      if (status === "completed") {
        const data = input.query.data as
          | { provider?: string; model?: string; documents_used?: string[] }
          | undefined;
        detail =
          data && "provider" in data
            ? `provider=${data.provider}/${data.model ?? "?"} · ${
                Array.isArray(data.documents_used) ? data.documents_used.length : 0
              } docs`
            : undefined;
      } else if (status === "error") {
        const err = input.query.error as { code?: string; message?: string } | undefined;
        detail = err?.code ?? "UNKNOWN";
      }

      fresh.push({
        seq: ++seqRef.current,
        at: new Date().toISOString(),
        agent: input.agent,
        status,
        detail,
      });
    }
    if (fresh.length) setEvents((prev) => [...prev.slice(-60), ...fresh]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, ...inputs.map((i) => deriveStatus(i.lifecycle))]);

  return events;
}
