"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef } from "react";
import type { OpsEvent } from "@/lib/ops-trace";

const STATUS_COLOR: Record<OpsEvent["status"], string> = {
  idle: "text-muted-foreground/40",
  searching: "text-cyan-400",
  analyzing: "text-blue-400",
  writing: "text-amber-400",
  debating: "text-violet-400",
  completed: "text-emerald-400",
  error: "text-red-400",
};

const STATUS_LABEL: Record<OpsEvent["status"], string> = {
  idle: "STANDBY",
  searching: "RETRIEVING",
  analyzing: "ANALYZING",
  writing: "GENERATING",
  debating: "DEBATING",
  completed: "COMPLETE",
  error: "ERROR",
};

/**
 * Full-height mission timeline sidebar.
 * Renders all OpsEvents from useOpsTrace, newest at bottom, auto-scrolling.
 * Persists for the session — history never erased during the session.
 */
export function MissionTimeline({ events }: { events: OpsEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  return (
    <div className="terminal-window flex h-full min-h-[300px] flex-col rounded-xl">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border/50 px-3 py-2.5">
        <div className="flex gap-1.5">
          <span className="status-dot animate-signal-pulse" style={{ backgroundColor: "hsl(var(--terminal-green))" }} />
        </div>
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          Mission Timeline
        </p>
        {events.length > 0 && (
          <span className="ml-auto font-mono text-[9px] text-muted-foreground/40">
            {events.length} events
          </span>
        )}
      </div>

      {/* Log body */}
      <div
        ref={scrollRef}
        role="log"
        aria-label="mission timeline"
        className="min-h-0 flex-1 overflow-y-auto p-3 font-mono text-[10px] leading-6"
      >
        {events.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 py-8 text-center">
            <motion.div
              animate={{ opacity: [0.3, 0.8, 0.3] }}
              transition={{ repeat: Infinity, duration: 2.5 }}
              className="font-mono text-[9px] uppercase tracking-[0.3em] text-muted-foreground/40"
            >
              AWAITING MISSION
            </motion.div>
            <div className="font-mono text-[9px] text-muted-foreground/25 tracking-widest">
              — no activity —
            </div>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((e) => (
              <motion.div
                key={e.seq}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="timeline-entry mb-1 grid grid-cols-[52px_1fr] gap-x-2"
              >
                {/* Timestamp */}
                <span className="text-muted-foreground/35 tabular-nums">
                  {e.at.slice(11, 19)}
                </span>

                {/* Event content */}
                <div className="space-y-0.5">
                  <div className="flex items-baseline gap-1.5 flex-wrap">
                    <span className="text-muted-foreground/60 truncate max-w-[80px]">
                      {e.agent.replace(" Agent", "").toUpperCase()}
                    </span>
                    <span className={`font-semibold tracking-widest ${STATUS_COLOR[e.status]}`}>
                      {STATUS_LABEL[e.status]}
                    </span>
                  </div>
                  {e.detail && (
                    <p className="text-muted-foreground/40 text-[9px] truncate">
                      {e.detail}
                    </p>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Footer */}
      {events.length > 0 && (
        <div className="border-t border-border/40 px-3 py-2">
          <span className="font-mono text-[9px] text-muted-foreground/30 tracking-widest">
            SESSION LOG · {events.length} RECORDS
          </span>
        </div>
      )}
    </div>
  );
}
