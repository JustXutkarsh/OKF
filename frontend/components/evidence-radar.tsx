"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";

/**
 * Evidence radar. While `searching` a sweeping arc rotates (an honest
 * "scanning" signal, not a fake counter). When documents arrive, real
 * blips pulse in, one per retrieved document. Angles are deterministic
 * (index across documents_used) so the visual is stable across rerenders.
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
        // Even angular spread scaled by stable id hash.
        const base = (i / Math.max(documents.length, 1)) * Math.PI * 2;
        let hash = 0;
        for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
        const angle = base + ((hash % 40) / 100 - 0.2);
        const radius = 26 + (hash % 22);
        return {
          id,
          x: 50 + Math.cos(angle) * radius,
          y: 50 + Math.sin(angle) * (radius * 0.72),
        };
      }),
    [documents]
  );

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[200px]">
      {/* Graticule rings */}
      <div className="absolute inset-0 rounded-full border border-foreground/10" />
      <div className="absolute inset-[18%] rounded-full border border-foreground/8" />
      <div className="absolute inset-[36%] rounded-full border border-foreground/6" />
      <div className="absolute inset-y-0 left-1/2 w-px bg-foreground/5" />
      <div className="absolute inset-x-0 top-1/2 h-px bg-foreground/5" />

      {/* Sweep while actively searching */}
      {active && (
        <motion.div
          className="absolute inset-0 origin-center rounded-full"
          style={{
            background:
              "conic-gradient(from 0deg, transparent 0deg, hsl(var(--signal) / 0.25) 40deg, transparent 80deg)",
          }}
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 2.4, ease: "linear" }}
          aria-hidden
        />
      )}

      {/* Blips: one per real retrieved document */}
      {dots.map((d) => (
        <motion.span
          key={d.id}
          title={d.id}
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: [0, 1, 0.7], scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="absolute size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            left: `${d.x}%`,
            top: `${d.y}%`,
            backgroundColor: "hsl(var(--signal) / 0.9)",
            boxShadow: "0 0 8px hsl(var(--signal) / 0.6)",
          }}
        />
      ))}

      {/* Center label */}
      <div className="absolute inset-0 flex items-center justify-center">
        <p className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
          {active
            ? "scanning"
            : documents.length
              ? `${documents.length} docs`
              : "no scan"}
        </p>
      </div>
    </div>
  );
}
