"use client";

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Circle } from "lucide-react";
import type { AgentLifecycle } from "@/lib/agent-lifecycle";

// Eight-stage mission execution pipeline, derived strictly from real AgentLifecycle state.
// Maps the 5 real stage indices to 8 visual steps with honest labeling:
// Steps 0-1: always complete first (mission received + retrieval started)
// Steps 2-3: map to stage 0 (retrieval/ranking)
// Steps 4-5: map to stages 1-2 (analysis)
// Steps 6-7: map to stages 3-4 (generation + verification)

const PIPELINE_STEPS = [
  { label: "MISSION RECEIVED", minStage: -1 },    // complete immediately
  { label: "RETRIEVING EVIDENCE", minStage: -1 }, // complete immediately
  { label: "RANKING DOCUMENTS", minStage: 0 },
  { label: "BUILDING CONTEXT", minStage: 0 },
  { label: "RUNNING ANALYSIS", minStage: 1 },
  { label: "GENERATING REPORT", minStage: 2 },
  { label: "CROSS-CHECKING CONFIDENCE", minStage: 3 },
  { label: "MISSION COMPLETE", minStage: 999 }, // only when done
] as const;

export function MissionPipeline({
  lifecycle,
  done,
}: {
  lifecycle: AgentLifecycle;
  done: boolean;
}) {
  const { stageIndex, phase } = lifecycle;

  // Determine which steps are done vs active vs pending
  const completedStepIndex = done
    ? PIPELINE_STEPS.length // all done
    : phase === "working"
      ? PIPELINE_STEPS.findIndex(
          (step, i) => step.minStage > stageIndex && i > 1
        )
      : 1; // idle: only first two shown as primed

  const activeIndex = done ? -1 : completedStepIndex;

  return (
    <div className="space-y-1.5 py-2 font-mono text-[11px]">
      <AnimatePresence initial={false}>
        {PIPELINE_STEPS.map((step, i) => {
          const isDone = done || i < completedStepIndex;
          const isActive = !done && i === activeIndex;

          return (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: i * 0.04 }}
              className="flex items-center gap-2.5"
            >
              {/* Step indicator */}
              {isDone ? (
                <CheckCircle2 className="size-3 shrink-0 pipeline-step-done" />
              ) : isActive ? (
                <motion.div
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 0.9 }}
                  className="size-3 shrink-0 rounded-full border"
                  style={{
                    borderColor: "hsl(var(--agent-color))",
                    backgroundColor: "hsl(var(--agent-color) / 0.3)",
                  }}
                />
              ) : (
                <Circle className="size-3 shrink-0 pipeline-step-pending" />
              )}

              {/* Step label */}
              <span
                className={`uppercase tracking-widest transition-colors ${
                  isDone
                    ? "pipeline-step-done"
                    : isActive
                      ? "pipeline-step-active font-semibold"
                      : "pipeline-step-pending"
                }`}
                style={isActive ? { color: "hsl(var(--agent-color))" } : undefined}
              >
                {isActive && "["}
                {step.label}
                {isActive && "]"}
              </span>

              {/* Active: trailing blink */}
              {isActive && (
                <motion.span
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ repeat: Infinity, duration: 0.7 }}
                  style={{ color: "hsl(var(--agent-color))" }}
                >
                  _
                </motion.span>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
