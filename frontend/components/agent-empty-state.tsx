"use client";

import { motion } from "framer-motion";
import { RadarIcon, ScaleIcon } from "lucide-react";
import { StaggerGroup, Reveal } from "@/components/reveal";

/**
 * Pre-question idle state: introduce the two agents before any work starts,
 * so the first Ask already feels like tasking a team.
 */
export function AgentEmptyState() {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-lg font-semibold tracking-tight">Ask a geopolitical question</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Two independent agents investigate the same auditable knowledge bundle in parallel.
        </p>
      </div>
      <StaggerGroup className="grid gap-4 md:grid-cols-2">
        <Reveal>
          <div
            className="glass rounded-2xl border p-5"
            style={{ borderColor: "hsl(var(--agent-brief) / 0.3)" }}
          >
            <div className="flex items-center gap-3">
              <div
                className="flex size-10 items-center justify-center rounded-lg border"
                style={{
                  borderColor: "hsl(var(--agent-brief) / 0.4)",
                  color: "hsl(var(--agent-brief))",
                }}
              >
                <RadarIcon className="size-5" />
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  AGENT://BRIEFING-01
                </p>
                <p className="text-sm font-semibold">Briefing Agent</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Provides grounded situation reports — current situation, key developments, key
              actors — each claim traced to documents and sources.
            </p>
          </div>
        </Reveal>
        <Reveal>
          <div
            className="glass rounded-2xl border p-5"
            style={{ borderColor: "hsl(var(--agent-analysis) / 0.3)" }}
          >
            <div className="flex items-center gap-3">
              <div
                className="flex size-10 items-center justify-center rounded-lg border"
                style={{
                  borderColor: "hsl(var(--agent-analysis) / 0.4)",
                  color: "hsl(var(--agent-analysis))",
                }}
              >
                <ScaleIcon className="size-5" />
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  AGENT://CRITIC-02
                </p>
                <p className="text-sm font-semibold">Critical Analysis Agent</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              Challenges assumptions and identifies uncertainty — conflicts, missing
              information, and where the evidence is thin.
            </p>
          </div>
        </Reveal>
      </StaggerGroup>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, transition: { delay: 0.3 } }}
        className="text-center font-mono text-xs text-muted-foreground/70"
      >
        ⌘ Both agents are standing by for your first question.
      </motion.p>
    </div>
  );
}
