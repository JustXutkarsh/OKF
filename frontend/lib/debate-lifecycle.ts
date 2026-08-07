"use client";

import { useEffect, useRef, useState } from "react";
import type { DebateMessage } from "@/lib/debate";

export type DebatePhase = "idle" | "debating" | "done";

// Debate phase controller. Driven exclusively by real state:
// - idle until both agents are done
// - debating while a message stream is revealed one-by-one (timers are
//   only the pacing; the CONTENT is data frozen after success)
// - done once all messages rendered
export function useDebatePhase(
  messages: DebateMessage[],
  bothDone: boolean,
  messageDelayMs = 900
): { phase: DebatePhase; visibleCount: number } {
  const [phase, setPhase] = useState<DebatePhase>("idle");
  const [visibleCount, setVisibleCount] = useState(0);
  const keyRef = useRef<string>("");

  // Reset when the message body changes (a new question was asked).
  const messagesKey = messages.map((m) => m.author + m.text).join("\n");
  if (keyRef.current !== messagesKey) {
    keyRef.current = messagesKey;
    setPhase(bothDone && messages.length > 0 ? "debating" : "idle");
    setVisibleCount(0);
  }

  useEffect(() => {
    if (!bothDone || messages.length === 0) return;
    if (phase !== "debating") return;
    if (visibleCount >= messages.length) {
      setPhase("done");
      return;
    }
    const id = window.setTimeout(
      () => setVisibleCount((n) => Math.min(messages.length, n + 1)),
      messageDelayMs
    );
    return () => window.clearTimeout(id);
  }, [bothDone, messages.length, messageDelayMs, phase, visibleCount]);

  return { phase, visibleCount };
}
