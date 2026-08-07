"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2 } from "lucide-react";
import type { AgentLifecycle } from "@/lib/agent-lifecycle";

/**
 * Vertical activity timeline: past stages marked done, current stage
 * pulsing. Labels describe the phase of work the agent is plausibly in —
 * honest about inactivity (only rendered while phase === "working").
 */
export function ActivityTimeline({ lifecycle }: { lifecycle: AgentLifecycle }) {
  const { stages, stageIndex } = lifecycle;

  // Show the last few stages up to the current one, with the tail of
  // earlier steps collapsed — keep the rail tight.
  const windowStart = Math.max(0, stageIndex - 1);
  const visible = stages.slice(0, stageIndex + 1).map((label, idx) => ({ label, idx }));
  const shown = visible.slice(windowStart);

  return (
    <div role="log" aria-label="agent activity" className="space-y-1 text-xs">
      {windowStart > 0 && (
        <p className="font-mono text-[10px] text-muted-foreground/60">
          +{windowStart} earlier step{windowStart > 1 ? "s" : ""}
        </p>
      )}
      <AnimatePresence initial={false} mode="popLayout">
        {shown.map(({ label, idx }) => {
          const active = idx === stageIndex;
          return (
            <motion.div
              key={`${idx}-${label}`}
              layout
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
              className="flex items-center gap-2"
            >
              {active ? (
                <Loader2
                  className="size-3.5 animate-spin"
                  style={{ color: "hsl(var(--agent-color))" }}
                />
              ) : (
                <CheckCircle2 className="size-3.5 text-muted-foreground/50" />
              )}
              <span className={active ? "font-medium" : "text-muted-foreground/70"}>
                {label}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
