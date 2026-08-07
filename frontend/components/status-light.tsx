"use client";

import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Search, ScanSearch, PenLine, Circle } from "lucide-react";
import type { AgentStatus } from "@/lib/agent-lifecycle";

const STATUS_META: Record<
  AgentStatus,
  { label: string; icon: typeof Circle; animated: boolean; color: string }
> = {
  idle: { label: "idle", icon: Circle, animated: false, color: "hsl(var(--muted-foreground))" },
  searching: { label: "searching", icon: Search, animated: true, color: "hsl(var(--agent-color))" },
  analyzing: { label: "analyzing", icon: ScanSearch, animated: true, color: "hsl(var(--agent-color))" },
  writing: { label: "writing", icon: PenLine, animated: true, color: "hsl(var(--agent-color))" },
  completed: { label: "completed", icon: CheckCircle2, animated: false, color: "hsl(164 86% 40%)" },
  error: { label: "error", icon: XCircle, animated: false, color: "hsl(var(--destructive))" },
};

/**
 * Animated state indicator: idle (dim dot) → searching/analyzing/writing
 * (pulsing agent-color icon) → completed (steady check) / error (steady x).
 * Uses the per-agent --agent-color so identity reads instantly.
 */
export function StatusLight({ status }: { status: AgentStatus }) {
  const { label, icon: Icon, animated, color } = STATUS_META[status];

  return (
    <div
      role="status"
      aria-label={`agent status: ${label}`}
      className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest"
      style={{ color }}
    >
      <motion.span
        animate={animated ? { opacity: [1, 0.35, 1] } : { opacity: 1 }}
        transition={animated ? { repeat: Infinity, duration: 1.4 } : {}}
        className="flex"
      >
        {status === "idle" ? (
          <span className="inline-block size-2 rounded-full bg-muted-foreground/50" />
        ) : status === "completed" ? (
          <Icon className="size-3.5" />
        ) : status === "error" ? (
          <Icon className="size-3.5" />
        ) : (
          <Icon className="size-3.5" />
        )}
      </motion.span>
      {status === "writing" ? (
        // Writing pulses like a stream — three dots rhythm.
        <span className="flex gap-0.5" aria-hidden>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              animate={{ opacity: [0.2, 1, 0.2] }}
              transition={{ repeat: Infinity, duration: 0.9, delay: i * 0.15 }}
              className="inline-block size-1 rounded-full"
              style={{ backgroundColor: color }}
            />
          ))}
        </span>
      ) : (
        <span
          className={animated ? "animate-pulse inline-block size-2 rounded-full" : ""}
          style={animated ? { backgroundColor: color } : undefined}
        />
      )}
      {label}
    </div>
  );
}
