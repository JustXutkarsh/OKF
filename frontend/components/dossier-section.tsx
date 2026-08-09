"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";

export type DossierClassification =
  | "VERIFIED"
  | "CONTESTED"
  | "CRITICAL"
  | "UNCERTAIN"
  | "CLASSIFIED"
  | "RESTRICTED"
  | "GAP"
  | "ACTORS";

const CLASSIFICATION_STYLE: Record<
  DossierClassification,
  { label: string; color: string; bg: string }
> = {
  VERIFIED: {
    label: "VERIFIED",
    color: "hsl(var(--terminal-green))",
    bg: "hsl(var(--terminal-green) / 0.08)",
  },
  CONTESTED: {
    label: "CONTESTED",
    color: "hsl(var(--terminal-amber))",
    bg: "hsl(var(--terminal-amber) / 0.08)",
  },
  CRITICAL: {
    label: "CRITICAL",
    color: "hsl(var(--terminal-red))",
    bg: "hsl(var(--terminal-red) / 0.08)",
  },
  UNCERTAIN: {
    label: "UNCERTAIN",
    color: "hsl(var(--terminal-amber))",
    bg: "hsl(var(--terminal-amber) / 0.06)",
  },
  CLASSIFIED: {
    label: "CLASSIFIED",
    color: "hsl(var(--agent-brief))",
    bg: "hsl(var(--agent-brief) / 0.08)",
  },
  RESTRICTED: {
    label: "RESTRICTED",
    color: "hsl(var(--agent-analysis))",
    bg: "hsl(var(--agent-analysis) / 0.08)",
  },
  GAP: {
    label: "INTELLIGENCE GAP",
    color: "hsl(var(--terminal-red) / 0.8)",
    bg: "hsl(var(--terminal-red) / 0.05)",
  },
  ACTORS: {
    label: "KEY ACTORS",
    color: "hsl(var(--terminal-cyan))",
    bg: "hsl(var(--terminal-cyan) / 0.07)",
  },
};

interface DossierSectionProps {
  title: string;
  classification?: DossierClassification;
  children: ReactNode;
  /** Optional right-side element (count badge, icon, etc.) */
  action?: ReactNode;
  /** Accent left-border color — defaults to muted */
  accentColor?: string;
  className?: string;
}

/**
 * Classified dossier section — replaces generic SectionCard for report content.
 * Features: classified header stamp, accent border, dark terminal aesthetic.
 */
export function DossierSection({
  title,
  classification,
  children,
  action,
  accentColor,
  className = "",
}: DossierSectionProps) {
  const cls = classification ? CLASSIFICATION_STYLE[classification] : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={`overflow-hidden rounded-lg border border-border/50 bg-card/40 ${className}`}
      style={accentColor ? { borderLeftColor: accentColor, borderLeftWidth: 2 } : undefined}
    >
      {/* Section header */}
      <div className="flex items-center gap-3 border-b border-border/40 bg-muted/20 px-4 py-2.5">
        <h3 className="flex-1 font-mono text-[10px] font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          {title}
        </h3>
        {cls && (
          <span
            className="rounded border px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest"
            style={{ color: cls.color, borderColor: `${cls.color}40`, backgroundColor: cls.bg }}
          >
            {cls.label}
          </span>
        )}
        {action && <div className="shrink-0">{action}</div>}
      </div>

      {/* Content */}
      <div className="px-4 py-3">{children}</div>
    </motion.div>
  );
}

/** Numbered intelligence item — used in key developments, actors, etc. */
export function IntelItem({
  index,
  text,
  color,
}: {
  index: number;
  text: string;
  color?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05 }}
      className="flex gap-3 py-1.5 text-sm"
    >
      <span
        className="shrink-0 font-mono text-[10px] tabular-nums leading-5"
        style={{ color: color ?? "hsl(var(--muted-foreground) / 0.5)" }}
      >
        {String(index + 1).padStart(2, "0")}
      </span>
      <span className="leading-relaxed text-foreground/90">{text}</span>
    </motion.div>
  );
}

/** Warning callout for contested/uncertain items */
export function IntelAlert({
  text,
  kind = "warning",
}: {
  text: string;
  kind?: "warning" | "danger" | "info";
}) {
  const styles = {
    warning: {
      border: "hsl(var(--terminal-amber) / 0.3)",
      bg: "hsl(var(--terminal-amber) / 0.05)",
      text: "hsl(var(--terminal-amber))",
      marker: "▲",
    },
    danger: {
      border: "hsl(var(--terminal-red) / 0.3)",
      bg: "hsl(var(--terminal-red) / 0.05)",
      text: "hsl(var(--terminal-red))",
      marker: "✗",
    },
    info: {
      border: "hsl(var(--terminal-cyan) / 0.3)",
      bg: "hsl(var(--terminal-cyan) / 0.05)",
      text: "hsl(var(--terminal-cyan))",
      marker: "▸",
    },
  };
  const s = styles[kind];
  return (
    <div
      className="flex gap-2.5 rounded border-l-2 px-3 py-2 text-sm"
      style={{ borderLeftColor: s.border, backgroundColor: s.bg }}
    >
      <span className="shrink-0 font-mono text-[11px]" style={{ color: s.text }}>
        {s.marker}
      </span>
      <span className="leading-relaxed text-foreground/80">{text}</span>
    </div>
  );
}
