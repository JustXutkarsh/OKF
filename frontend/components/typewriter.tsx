"use client";

import { useEffect, useState } from "react";

/**
 * Typewriter reveal for the agent's *final* answer text. The text is fully
 * available (backend does not stream) — this is a presentation effect on
 * an already-arrived string, not faked streaming. Respects
 * prefers-reduced-motion: renders instantly.
 */
export function Typewriter({
  text,
  speed = 14,
  className,
}: {
  text: string;
  /** ms per character chunk */
  speed?: number;
  className?: string;
}) {
  const [revealed, setRevealed] = useState(0);
  const [instant, setInstant] = useState(false);

  useEffect(() => {
    // Some environments (tests, SSR edges) may lack matchMedia — degrade
    // gracefully to full text rather than crash inside render effects.
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      setInstant(true);
      return;
    }
    setInstant(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  useEffect(() => {
    if (instant || revealed >= text.length) return;
    const id = window.setTimeout(() => {
      // Reveal a few chars per tick for a *section* pace, not character-slow.
      setRevealed((n) => Math.min(text.length, n + 6));
    }, speed);
    return () => window.clearTimeout(id);
  }, [revealed, text.length, speed, instant]);

  const done = instant || revealed >= text.length;
  return (
    <span className={className}>
      {done ? text : text.slice(0, revealed)}
      {!done && <span className="caret" aria-hidden />}
    </span>
  );
}
