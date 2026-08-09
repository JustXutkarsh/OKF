"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { AgentLifecycle } from "@/lib/agent-lifecycle";

/**
 * Terminal stream console — renders past stages as scrollable console output,
 * current stage pulsing. Used inside AgentPanel while phase === "working".
 */
export function ActivityTimeline({ lifecycle }: { lifecycle: AgentLifecycle }) {
  const { stages, stageIndex } = lifecycle;
  const shown = stages.slice(0, stageIndex + 1).map((label, idx) => ({ label, idx }));

  return (
    <div role="log" aria-label="agent activity" className="space-y-1 font-mono text-[11px]">
      <AnimatePresence initial={false} mode="popLayout">
        {shown.map(({ label, idx }) => {
          const active = idx === stageIndex;
          return (
            <motion.div
              key={`${idx}-${label}`}
              layout
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.22 }}
              className="flex items-center gap-2"
            >
              <span
                style={{
                  color: active
                    ? "hsl(var(--agent-color))"
                    : "hsl(var(--terminal-green))",
                }}
                className="shrink-0"
              >
                {active ? "▸" : "✓"}
              </span>
              <span
                style={{
                  color: active
                    ? "hsl(var(--agent-color))"
                    : "hsl(var(--muted-foreground) / 0.55)",
                }}
              >
                {label}
              </span>
              {active && (
                <motion.span
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ repeat: Infinity, duration: 0.8 }}
                  style={{ color: "hsl(var(--agent-color))" }}
                >
                  _
                </motion.span>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
