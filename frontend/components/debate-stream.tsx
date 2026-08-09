"use client";

import { AnimatePresence, motion } from "framer-motion";
import { RadarIcon, ScaleIcon, Swords, AlertTriangle, CheckCircle2, HelpCircle, Lightbulb } from "lucide-react";
import { useMemo, useState } from "react";
import { buildDebateMessages, type DebateMessage } from "@/lib/debate";
import { useDebatePhase } from "@/lib/debate-lifecycle";
import type { Analysis, Briefing } from "@/lib/types";

const AGENT_META = {
  briefing: {
    label: "BRIEFING-01",
    shortLabel: "BRIEF",
    Icon: RadarIcon,
    color: "hsl(var(--agent-brief))",
    side: "left" as const,
  },
  critic: {
    label: "CRITIC-02",
    shortLabel: "CRITIC",
    Icon: ScaleIcon,
    color: "hsl(var(--agent-analysis))",
    side: "right" as const,
  },
} as const;

type DebateTab = "exchange" | "agreements" | "conflicts" | "gaps" | "alternatives";

const TABS: { id: DebateTab; label: string; icon: typeof Swords }[] = [
  { id: "exchange", label: "EXCHANGE", icon: Swords },
  { id: "agreements", label: "AGREEMENTS", icon: CheckCircle2 },
  { id: "conflicts", label: "CONTESTED", icon: AlertTriangle },
  { id: "gaps", label: "GAPS", icon: HelpCircle },
  { id: "alternatives", label: "ALTERNATIVES", icon: Lightbulb },
];

function DebateMessageCard({ msg, index }: { msg: DebateMessage; index: number }) {
  const meta = AGENT_META[msg.author];
  const isRight = meta.side === "right";

  return (
    <motion.div
      initial={{ opacity: 0, x: isRight ? 12 : -12, y: 4 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1], delay: index * 0.02 }}
      className={`flex ${isRight ? "justify-end" : "justify-start"}`}
    >
      <div
        className="max-w-[88%] rounded-lg border bg-card/40 px-3.5 py-2.5"
        style={{
          borderColor: msg.disagreement
            ? "hsl(var(--terminal-amber) / 0.4)"
            : `${meta.color.replace(")", " / 0.25)")}`,
          backgroundColor: msg.disagreement
            ? "hsl(var(--terminal-amber) / 0.04)"
            : undefined,
        }}
      >
        <div className="mb-1.5 flex items-center gap-1.5">
          <meta.Icon className="size-3 shrink-0" style={{ color: meta.color }} />
          <span
            className="font-mono text-[9px] uppercase tracking-[0.2em] font-semibold"
            style={{ color: meta.color }}
          >
            {meta.label}
          </span>
          {msg.disagreement && (
            <span className="ml-1 rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wide text-amber-400">
              CONTESTED
            </span>
          )}
          {msg.kind === "challenge" && !msg.disagreement && (
            <span className="ml-1 font-mono text-[8px] uppercase tracking-wide text-muted-foreground/40">
              CHALLENGE
            </span>
          )}
        </div>
        <p className="text-sm leading-relaxed text-foreground/85">{msg.text}</p>
        {msg.detail && (
          <p className="mt-1.5 font-mono text-[9px] text-muted-foreground/40">{msg.detail}</p>
        )}
      </div>
    </motion.div>
  );
}

export function DebateStream({
  briefing,
  analysis,
}: {
  briefing: Briefing;
  analysis: Analysis;
}) {
  const [activeTab, setActiveTab] = useState<DebateTab>("exchange");
  const messages = useMemo(() => buildDebateMessages(briefing, analysis), [briefing, analysis]);
  const { visibleCount } = useDebatePhase(messages, true, 800);
  const visible = messages.slice(0, visibleCount);

  const agreements = messages.filter((m) => !m.disagreement);
  const conflicts = messages.filter((m) => m.disagreement);
  const critic = analysis.critical_analysis;
  const gaps = critic.missing_information;
  const alternatives = critic.alternative_interpretations;
  const disagreementCount = conflicts.length;

  return (
    <div className="terminal-window flex flex-col rounded-xl min-h-[380px]">
      {/* Header */}
      <div className="flex items-center gap-2.5 border-b border-border/50 px-4 py-3">
        <div className="flex gap-1.5">
          <span className="status-dot" style={{ backgroundColor: "hsl(var(--agent-brief))" }} />
          <span className="status-dot" style={{ backgroundColor: "hsl(var(--agent-analysis))" }} />
        </div>
        <Swords className="size-3.5 text-muted-foreground/60" />
        <p className="flex-1 font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          AI DEBATE ROOM
        </p>
        {disagreementCount > 0 && (
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 font-mono text-[9px] text-amber-400"
          >
            {disagreementCount} CONTESTED
          </motion.span>
        )}
      </div>

      {/* Tab Bar */}
      <div className="flex border-b border-border/40 bg-muted/10 overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const count =
            tab.id === "conflicts"
              ? conflicts.length
              : tab.id === "agreements"
                ? agreements.length
                : tab.id === "gaps"
                  ? gaps.length
                  : tab.id === "alternatives"
                    ? alternatives.length
                    : null;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-1 shrink-0 items-center justify-center gap-1.5 px-3 py-2.5 font-mono text-[9px] uppercase tracking-widest transition-colors ${
                activeTab === tab.id
                  ? "border-b-2 border-cyan-400 text-foreground font-bold"
                  : "text-muted-foreground/50 hover:text-muted-foreground"
              }`}
            >
              <Icon className="size-3" />
              <span>{tab.label}</span>
              {count !== null && count > 0 && (
                <span className="rounded-full bg-muted/60 px-1.5 text-[8px]">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="min-h-0 flex-1 overflow-y-auto p-4" role="log" aria-label="debate chamber">
        <AnimatePresence mode="wait">
          {activeTab === "exchange" && (
            <motion.div
              key="exchange"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              {visible.map((msg, i) => (
                <DebateMessageCard key={`${i}-${msg.author}`} msg={msg} index={i} />
              ))}
              {visibleCount < messages.length && (
                <div className="flex items-center gap-2 px-1 font-mono text-[10px] text-muted-foreground/40">
                  <motion.span
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                    className="size-1.5 rounded-full bg-muted-foreground/50"
                  />
                  agents exchanging positions…
                </div>
              )}
            </motion.div>
          )}

          {activeTab === "agreements" && (
            <motion.div
              key="agreements"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-2.5"
            >
              {agreements.length === 0 ? (
                <p className="py-6 text-center font-mono text-[10px] text-muted-foreground/40">
                  AWAITING ANALYSIS…
                </p>
              ) : (
                agreements.map((msg, i) => (
                  <div
                    key={i}
                    className="flex gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3"
                  >
                    <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-emerald-400" />
                    <div>
                      <p className="font-mono text-[9px] uppercase tracking-wide text-emerald-400 font-semibold mb-1">
                        {AGENT_META[msg.author].label} · AGREEMENT
                      </p>
                      <p className="text-sm leading-relaxed text-foreground/85">{msg.text}</p>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}

          {activeTab === "conflicts" && (
            <motion.div
              key="conflicts"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              {conflicts.length === 0 ? (
                <p className="py-6 text-center font-mono text-[10px] text-muted-foreground/40">
                  NO CONFLICTS DETECTED
                </p>
              ) : (
                <>
                  {conflicts.map((msg, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3"
                    >
                      <div className="mb-2 flex items-center gap-2">
                        <AlertTriangle className="size-3 text-amber-400" />
                        <span className="font-mono text-[9px] uppercase tracking-wide text-amber-400 font-semibold">
                          {AGENT_META[msg.author].label} · CONTESTED CLAIM
                        </span>
                      </div>
                      <p className="text-sm leading-relaxed text-foreground/85">{msg.text}</p>
                    </div>
                  ))}
                  {critic.conflicting_evidence.map((c, i) => (
                    <div
                      key={`conflict-ev-${i}`}
                      className="rounded-lg border border-red-500/25 bg-red-500/5 p-3"
                    >
                      <p className="mb-2 font-mono text-[9px] uppercase tracking-wide text-red-400 font-semibold">
                        EVIDENCE CONFLICT · {c.description}
                      </p>
                      <div className="space-y-2 text-sm">
                        <div className="border-l-2 border-emerald-500/50 pl-3 text-foreground/80">
                          {c.supporting_text}
                        </div>
                        <div className="border-l-2 border-red-500/50 pl-3 text-foreground/80">
                          {c.conflicting_text}
                        </div>
                      </div>
                    </div>
                  ))}
                </>
              )}
            </motion.div>
          )}

          {activeTab === "gaps" && (
            <motion.div
              key="gaps"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <div>
                <p className="mb-2 font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/50">
                  MISSING INTELLIGENCE GAPS
                </p>
                {gaps.length === 0 ? (
                  <p className="font-mono text-[10px] text-muted-foreground/40">
                    No gaps identified.
                  </p>
                ) : (
                  gaps.map((gap, i) => (
                    <div
                      key={i}
                      className="mb-2 flex gap-2.5 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-sm"
                    >
                      <span className="shrink-0 font-mono text-[11px] text-red-400">✗</span>
                      <p className="leading-relaxed text-foreground/80">{gap}</p>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          )}

          {activeTab === "alternatives" && (
            <motion.div
              key="alternatives"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-2.5"
            >
              {alternatives.length === 0 ? (
                <p className="py-6 text-center font-mono text-[10px] text-muted-foreground/40">
                  NO ALTERNATIVE INTERPRETATIONS FLAGGED
                </p>
              ) : (
                alternatives.map((alt, i) => (
                  <div
                    key={i}
                    className="flex gap-2.5 rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3 text-sm"
                  >
                    <Lightbulb className="mt-0.5 size-3.5 shrink-0 text-cyan-400" />
                    <p className="leading-relaxed text-foreground/85">{alt}</p>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
