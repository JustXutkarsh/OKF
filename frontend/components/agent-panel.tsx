"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { deriveStatus, type AgentLifecycle } from "@/lib/agent-lifecycle";
import { ActivityTimeline } from "@/components/activity-timeline";
import { EvidenceScan } from "@/components/evidence-scan";
import { StatusLight } from "@/components/status-light";
import type { LucideIcon } from "lucide-react";

export interface AgentIdentity {
  /** Internal name shown as mono eyebrow, e.g. "AGENT://BRIEFING-01" */
  callsign: string;
  /** Human title, e.g. "Briefing Agent" */
  title: string;
  /** One-line role statement. */
  role: string;
  Icon: LucideIcon;
  /** HSL triple string for --agent-color, e.g. "var(--agent-brief)". */
  color: string;
  phases: string[]; // working-stage labels for ActivityTimeline
}

const STATUS_COPY: Record<AgentLifecycle["phase"], string> = {
  idle: "standby",
  working: "live",
  done: "report ready",
  error: "signal lost",
};

/**
 * One agent's workspace: identity header (avatar, callsign, live-status chip),
 * status light, the activity timeline while working, then the report body.
 * Everything is framed by the agent's accent color so two agents are
 * instantly legible.
 */
export function AgentPanel({
  agent,
  lifecycle,
  children,
}: {
  agent: AgentIdentity;
  lifecycle: AgentLifecycle;
  children: ReactNode;
}) {
  const { phase } = lifecycle;
  const busy = phase === "working";
  const status = deriveStatus(lifecycle);

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      style={{ "--agent-color": agent.color } as React.CSSProperties}
      className={`glass flex min-h-[280px] flex-col overflow-hidden rounded-2xl border ${busy ? "agent-ring agent-glow" : ""}`}
      aria-label={agent.title}
    >
      {/* Agent header: identity + live status */}
      <header className="flex items-start gap-3 border-b p-4">
        <div
          className={`flex size-9 shrink-0 items-center justify-center rounded-lg border bg-background/60 ${busy ? "agent-glow" : ""}`}
          style={{ color: `hsl(${agent.color})` }}
        >
          <agent.Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              {agent.callsign}
            </p>
            <StatusLight status={status} />
          </div>
          <div className="flex items-center gap-2">
            <h2 className="truncate text-sm font-semibold">{agent.title}</h2>
            <motion.span
              layout
              animate={busy ? { opacity: [1, 0.4, 1] } : { opacity: 1 }}
              transition={busy ? { repeat: Infinity, duration: 1.2 } : {}}
              className="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide"
              style={{
                color: `hsl(${agent.color})`,
                borderColor: `hsl(${agent.color} / 0.35)`,
                backgroundColor: `hsl(${agent.color} / 0.08)`,
              }}
            >
              {STATUS_COPY[phase]}
            </motion.span>
          </div>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{agent.role}</p>
        </div>
      </header>

      {/* Working state: live timeline, then evidence-scan shimmer. */}
      <div className="min-h-0 flex-1">
        {busy && (
          <div className="border-b p-3">
            <ActivityTimeline lifecycle={lifecycle} />
            <div className="mt-3">
              <EvidenceScan active={busy} />
            </div>
          </div>
        )}
        <div className="p-4">{children}</div>
      </div>
    </motion.section>
  );
}
