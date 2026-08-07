"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Terminal } from "lucide-react";
import { useEffect, useRef } from "react";
import type { OpsEvent } from "@/lib/ops-trace";

const STATUS_COLOR: Record<OpsEvent["status"], string> = {
  idle: "text-muted-foreground/60",
  searching: "text-cyan-300",
  analyzing: "text-cyan-200",
  writing: "text-amber-300",
  completed: "text-emerald-300",
  error: "text-red-300",
};

/**
 * Live operations feed: one line per agent state transition, newest at the
 * bottom, auto-scrolling. Production-visible (replaces the dev DebugPanel);
 * shows statuses only — never API keys, contents, or question text.
 */
export function OpsLog({ events }: { events: OpsEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  return (
    <div className="glass rounded-xl border">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Terminal className="size-3.5 text-muted-foreground" />
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          Agent activity log
        </p>
        {events.length > 0 && (
          <p className="ml-auto font-mono text-[10px] text-muted-foreground/60">
            {events.length} events
          </p>
        )}
      </div>
      <div
        ref={scrollRef}
        role="log"
        aria-label="agent activity log"
        className="h-28 overflow-y-auto p-3 font-mono text-[11px] leading-5"
      >
        {events.length === 0 ? (
          <p className="text-muted-foreground/50">— no activity yet —</p>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((e) => (
              <motion.div
                key={e.seq}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="flex gap-3"
              >
                <span className="shrink-0 text-muted-foreground/50">
                  {e.at.slice(11, 19)}
                </span>
                <span className="w-28 shrink-0 truncate text-muted-foreground">
                  {e.agent}
                </span>
                <span className={`w-24 shrink-0 ${STATUS_COLOR[e.status]}`}>
                  {e.status}
                </span>
                {e.detail && (
                  <span className="truncate text-muted-foreground/70">{e.detail}</span>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
