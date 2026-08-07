"use client";

import { AnimatePresence, motion } from "framer-motion";
import { RadarIcon, ScaleIcon, Swords } from "lucide-react";
import { useMemo } from "react";
import { buildDebateMessages, type DebateMessage } from "@/lib/debate";
import { useDebatePhase } from "@/lib/debate-lifecycle";
import type { Analysis, Briefing } from "@/lib/types";

const AGENT_META = {
  briefing: {
    label: "Briefing Agent",
    Icon: RadarIcon,
    color: "hsl(var(--agent-brief))",
    align: "justify-start",
    bubble: "bg-background/50",
    accent: "border",
  },
  critic: {
    label: "Critical Critic",
    Icon: ScaleIcon,
    color: "hsl(var(--agent-analysis))",
    align: "justify-end",
    bubble: "bg-background/50",
    accent: "border",
  },
} as const;

/** Debate stream: agent messages appear one-by-one as a conversation. */
export function DebateStream({
  briefing,
  analysis,
}: {
  briefing: Briefing;
  analysis: Analysis;
}) {
  const messages = useMemo(
    () => buildDebateMessages(briefing, analysis),
    [briefing, analysis]
  );
  const { visibleCount } = useDebatePhase(messages, true, 900);
  const visible = messages.slice(0, visibleCount);
  const disagreements = messages.filter((m) => m.disagreement).length;

  return (
    <div className="glass flex h-full min-h-[320px] flex-col rounded-2xl border">
      <div className="flex items-center gap-2 border-b p-3">
        <Swords className="size-4 text-muted-foreground" />
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          Debate stream
        </p>
        {disagreements > 0 && (
          <p className="ml-auto rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-300">
            {disagreements} shift{disagreements === 1 ? "" : "s"}
          </p>
        )}
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3" role="log" aria-label="debate transcript">
        <AnimatePresence initial={false}>
          {visible.map((msg, i) => {
            const meta = AGENT_META[msg.author];
            return (
              <motion.div
                key={`${i}-${msg.author}-${msg.text.slice(0, 24)}`}
                initial={{ opacity: 0, y: 12, x: msg.author === "critic" ? 12 : -12 }}
                animate={{ opacity: 1, y: 0, x: 0 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className={`flex ${meta.align}`}
              >
                <div
                  className={`max-w-[85%] rounded-xl border p-3 text-sm ${meta.bubble} ${meta.accent}`}
                  style={{ borderColor: `${meta.color.replace("hsl", "hsl").replace(")", " / 0.3)")}` }}
                >
                  <p
                    className="mb-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.15em]"
                    style={{ color: meta.color }}
                  >
                    <meta.Icon className="size-3" />
                    {meta.label}
                    {msg.disagreement && (
                      <span className="ml-1 rounded-full bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-300">
                        shift
                      </span>
                    )}
                  </p>
                  <p className="leading-relaxed text-foreground/95">{msg.text}</p>
                  {msg.detail && (
                    <p className="mt-1.5 text-[10px] text-muted-foreground/70">{msg.detail}</p>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        {visibleCount < messages.length && (
          <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground/60">
            <span className="inline-block size-1 rounded-full bg-muted-foreground animate-pulse" />
            agents exchanging positions…
          </div>
        )}
      </div>
    </div>
  );
}
