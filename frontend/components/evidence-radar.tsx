"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";

/**
 * Evidence radar — upgraded with agent-color sweep and enhanced blip glow.
 * Sweep active while agent is searching; blips pulse in on document arrival.
 */
export function EvidenceRadar({
  active,
  documents,
}: {
  active: boolean;
  documents: string[];
}) {
  const dots = useMemo(
    () =>
      documents.map((id, i) => {
        const base = (i / Math.max(documents.length, 1)) * Math.PI * 2;
        let hash = 0;
        for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
        const angle = base + ((hash % 40) / 100 - 0.2);
        const radius = 26 + (hash % 22);
        return {
          id,
          x: 50 + Math.cos(angle) * radius,
          y: 50 + Math.sin(angle) * (radius * 0.72),
          delay: (hash % 8) * 0.06,
        };
      }),
    [documents]
  );

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[180px]">
      {/* Graticule rings */}
      <div className="absolute inset-0 rounded-full border border-foreground/8" />
      <div className="absolute inset-[18%] rounded-full border border-foreground/6" />
      <div className="absolute inset-[36%] rounded-full border border-foreground/5" />
      {/* Cross hairs */}
      <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/5" />
      <div className="absolute inset-x-0 top-1/2 h-px bg-foreground/5" />

      {/* Sweep while actively searching */}
      {active && (
        <>
          <motion.div
            className="absolute inset-0 origin-center rounded-full"
            style={{
              background:
                "conic-gradient(from 0deg, transparent 0deg, hsl(var(--agent-color) / 0.2) 50deg, transparent 90deg)",
            }}
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 2.4, ease: "linear" }}
            aria-hidden
          />
          {/* Ping ring */}
          <motion.div
            className="absolute inset-[28%] rounded-full border"
            style={{ borderColor: "hsl(var(--agent-color) / 0.4)" }}
            animate={{ opacity: [0.6, 0, 0.6], scale: [0.9, 1.3, 0.9] }}
            transition={{ repeat: Infinity, duration: 2.4, ease: "easeOut" }}
            aria-hidden
          />
        </>
      )}

      {/* Blips: one per retrieved document */}
      {dots.map((d) => (
        <motion.span
          key={d.id}
          title={d.id}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: [0, 1, 0.8], scale: 1 }}
          transition={{ duration: 0.5, delay: d.delay }}
          className="absolute size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            left: `${d.x}%`,
            top: `${d.y}%`,
            backgroundColor: "hsl(var(--signal) / 0.9)",
            boxShadow: "0 0 6px 2px hsl(var(--signal) / 0.5)",
          }}
        />
      ))}

      {/* Center label */}
      <div className="absolute inset-0 flex items-center justify-center">
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground/50">
          {active ? "SCANNING" : documents.length ? `${documents.length} DOCS` : "READY"}
        </p>
      </div>
    </div>
  );
}
