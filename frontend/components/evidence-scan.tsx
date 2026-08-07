"use client";

import { motion } from "framer-motion";

/**
 * Evidence-retrieval shimmer: stacked blocks that sequentially glow while
 * the agent is actually waiting on retrieval. Not a fake progress meter —
 * animated while `active` (the retrieval stage is happening), inert
 * otherwise. Communicates "scanning documents" before real evidence lands.
 */
export function EvidenceScan({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div aria-hidden className="space-y-1.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.2, width: "30%" }}
          animate={
            active
              ? { opacity: [0.25, 0.85, 0.25], width: ["30%", "62%", "30%"] }
              : { opacity: 0.2 }
          }
          transition={{
            repeat: Infinity,
            duration: 2.2,
            delay: i * 0.25,
            ease: "easeInOut",
          }}
          className="h-2 rounded"
          style={{ backgroundColor: "hsl(var(--agent-color) / 0.25)" }}
        />
      ))}
      <p className="font-mono text-[10px] text-muted-foreground/70">
        scanning documents…
      </p>
    </div>
  );
}
