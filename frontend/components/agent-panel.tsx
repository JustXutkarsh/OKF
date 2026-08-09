"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { ReactNode } from "react";
import { deriveStatus, type AgentLifecycle } from "@/lib/agent-lifecycle";
import { MissionPipeline } from "@/components/mission-pipeline";
import { RadarIcon, ScaleIcon, type LucideIcon } from "lucide-react";
import type { Briefing, Analysis } from "@/lib/types";

export interface AgentIdentity {
  callsign: string;
  title: string;
  role: string;
  Icon: LucideIcon;
  color: string;
  phases: string[];
}

export const BRIEFING_AGENT: AgentIdentity = {
  callsign: "AGENT://BRIEFING-01",
  title: "Briefing Agent",
  role: "Synthesizes grounded situation reports from retrieved documents.",
  Icon: RadarIcon,
  color: "var(--agent-brief)",
  phases: [
    "Searching knowledge base…",
    "Retrieving documents…",
    "Evaluating evidence…",
    "Constructing response…",
    "Validating sources…",
  ],
};

export const ANALYSIS_AGENT: AgentIdentity = {
  callsign: "AGENT://CRITIC-02",
  title: "Critical Analysis Agent",
  role: "Challenges assumptions and surfaces uncertainty in the briefing.",
  Icon: ScaleIcon,
  color: "var(--agent-analysis)",
  phases: [
    "Scanning retrieved documents…",
    "Identifying assumptions…",
    "Cross-examining evidence…",
    "Identifying information gaps…",
    "Assessing confidence…",
  ],
};

const STATUS_BADGE: Record<AgentLifecycle["phase"], { label: string; blink: boolean }> = {
  idle: { label: "STANDBY", blink: false },
  working: { label: "ACTIVE", blink: true },
  debating: { label: "DEBATING", blink: true },
  done: { label: "COMPLETE", blink: false },
  error: { label: "ERR", blink: false },
};

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (el) {
    const top = el.getBoundingClientRect().top + window.scrollY - 70;
    window.scrollTo({ top, behavior: "smooth" });
  }
}

/**
 * Agent Panel: Handles active execution state (prominent pipeline + live logs)
 * and completed state (compact summary card with evidence overview & dossier scroll affordance).
 */
export function AgentPanel({
  agent,
  lifecycle,
  reportData,
  children,
}: {
  agent: AgentIdentity;
  lifecycle: AgentLifecycle;
  reportData?: Briefing | Analysis;
  children?: ReactNode;
}) {
  const { phase } = lifecycle;
  const busy = phase === "working";
  const done = phase === "done";
  const error = phase === "error";
  const badge = STATUS_BADGE[phase];
  const status = deriveStatus(lifecycle);

  const evidenceCount = reportData?.evidence?.length ?? 0;
  const topDocs = Array.from(
    new Set(reportData?.evidence?.map((e) => e.document_id) ?? [])
  ).slice(0, 3);
  const verifiedCount =
    reportData?.evidence?.filter((e) => e.confidence === "verified").length ?? 0;

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      style={{ "--agent-color": agent.color } as React.CSSProperties}
      className={`terminal-window flex flex-col rounded-xl transition-all ${
        busy ? "agent-ring agent-glow min-h-[380px]" : "min-h-[220px]"
      }`}
      aria-label={agent.title}
    >
      {/* ── Title bar ── */}
      <header
        className="relative flex items-center gap-3 border-b border-border/50 px-4 py-2.5"
        style={{ borderBottomColor: busy ? "hsl(var(--agent-color) / 0.25)" : undefined }}
      >
        <div className="flex gap-1.5">
          <span
            className="status-dot"
            style={{
              backgroundColor: error
                ? "hsl(var(--terminal-red))"
                : done
                  ? "hsl(var(--terminal-green))"
                  : "hsl(var(--agent-color) / 0.7)",
            }}
          >
            {busy && (
              <motion.span
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
                className="absolute inset-0 rounded-full"
                style={{ backgroundColor: "hsl(var(--agent-color))" }}
              />
            )}
          </span>
          <span className="status-dot bg-yellow-500/40" />
          <span className="status-dot bg-green-500/20" />
        </div>

        <p
          className="flex-1 font-mono text-[11px] font-semibold uppercase tracking-[0.2em]"
          style={{ color: "hsl(var(--agent-color))" }}
        >
          {agent.callsign}
        </p>

        <motion.span
          layout
          animate={badge.blink ? { opacity: [1, 0.4, 1] } : { opacity: 1 }}
          transition={badge.blink ? { repeat: Infinity, duration: 1.2 } : {}}
          className="shrink-0 rounded border px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest"
          style={{
            color: error
              ? "hsl(var(--terminal-red))"
              : done
                ? "hsl(var(--terminal-green))"
                : "hsl(var(--agent-color))",
            borderColor: error
              ? "hsl(var(--terminal-red) / 0.3)"
              : done
                ? "hsl(var(--terminal-green) / 0.3)"
                : "hsl(var(--agent-color) / 0.3)",
            backgroundColor: error
              ? "hsl(var(--terminal-red) / 0.07)"
              : done
                ? "hsl(var(--terminal-green) / 0.07)"
                : "hsl(var(--agent-color) / 0.07)",
          }}
        >
          {badge.label}
        </motion.span>
      </header>

      {/* ── Meta row ── */}
      <div className="flex items-center gap-3 border-b border-border/30 bg-muted/20 px-4 py-2">
        <agent.Icon
          className="size-3.5 shrink-0"
          style={{ color: "hsl(var(--agent-color) / 0.7)" }}
        />
        <p className="flex-1 font-mono text-[10px] text-muted-foreground/70 truncate">
          {reportData ? `${reportData.provider} / ${reportData.model}` : agent.role}
        </p>
        <span className="shrink-0 font-mono text-[9px] uppercase tracking-widest text-muted-foreground/40">
          {status}
        </span>
      </div>

      {/* ── Body ── */}
      <div className="relative min-h-0 flex-1 overflow-auto p-4">
        <AnimatePresence mode="wait">
          {busy ? (
            /* Active execution pipeline + live console logs */
            <motion.div
              key="busy"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              <div className="space-y-1 border-b border-border/30 pb-3">
                <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/50">
                  LIVE STREAM
                </p>
                <AnimatePresence initial={false}>
                  {lifecycle.stages.slice(0, lifecycle.stageIndex + 1).map((label, idx) => (
                    <motion.div
                      key={`${idx}-${label}`}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-2 font-mono text-[11px]"
                    >
                      <span
                        style={{
                          color:
                            idx === lifecycle.stageIndex
                              ? "hsl(var(--agent-color))"
                              : "hsl(var(--terminal-green))",
                        }}
                      >
                        {idx === lifecycle.stageIndex ? "▸" : "✓"}
                      </span>
                      <span
                        style={{
                          color:
                            idx === lifecycle.stageIndex
                              ? "hsl(var(--agent-color))"
                              : "hsl(var(--muted-foreground) / 0.6)",
                        }}
                      >
                        {label}
                      </span>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>

              <p className="font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/50">
                EXECUTION PIPELINE
              </p>
              <MissionPipeline lifecycle={lifecycle} done={false} />
            </motion.div>
          ) : done ? (
            /* Completed compact execution summary card */
            <motion.div
              key="done"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              {/* Pipeline completed indicator */}
              <div className="flex items-center justify-between rounded border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 font-mono text-[10px] text-emerald-400">
                <span className="flex items-center gap-1.5">
                  <span>✓</span> EXECUTION COMPLETED
                </span>
                <span>8 / 8 STAGES</span>
              </div>

              {/* Evidence summary */}
              <div className="rounded border border-border/40 bg-background/30 p-3 space-y-2">
                <div className="flex items-center justify-between font-mono text-[10px]">
                  <span className="uppercase tracking-widest text-muted-foreground/60">
                    EVIDENCE SUMMARY
                  </span>
                  <span style={{ color: "hsl(var(--agent-color))" }}>
                    {evidenceCount} FRAGMENTS ({verifiedCount} VERIFIED)
                  </span>
                </div>

                {topDocs.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {topDocs.map((doc, idx) => (
                      <span
                        key={`${doc}-${idx}`}
                        className="rounded border border-border/50 bg-muted/40 px-2 py-0.5 font-mono text-[9px] text-muted-foreground/70"
                      >
                        {doc}
                      </span>
                    ))}
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => scrollToSection("section-evidence")}
                  className="mt-1 font-mono text-[9px] uppercase tracking-widest text-cyan-400 hover:underline inline-flex items-center gap-1"
                >
                  VIEW FULL EVIDENCE ↗
                </button>
              </div>

              {/* View Dossier Action */}
              <div className="flex items-center justify-between pt-1">
                <span className="font-mono text-[9px] text-muted-foreground/40">
                  REPORT GENERATED & READY
                </span>
                <button
                  type="button"
                  onClick={() => scrollToSection("section-results")}
                  className="rounded border border-border/60 bg-muted/30 px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-foreground transition-all hover:bg-muted/60"
                  style={{ borderColor: "hsl(var(--agent-color) / 0.4)" }}
                >
                  VIEW DOSSIER ↓
                </button>
              </div>
            </motion.div>
          ) : (
            /* Standby / Idle / Error */
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {children}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}
