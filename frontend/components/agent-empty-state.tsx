"use client";

import { RadarIcon, ScaleIcon } from "lucide-react";

const BRIEFING_STREAMS = [
  "Monitoring geopolitical event feeds…",
  "Bundle index loaded. 0 active queries.",
  "Standing by for mission dispatch.",
];

const CRITIC_STREAMS = [
  "Critical analysis module initialized.",
  "Assumption-detection engine armed.",
  "Standing by for mission dispatch.",
];

function IdleTerminal({
  callsign,
  role,
  Icon,
  color,
  streams,
}: {
  callsign: string;
  role: string;
  Icon: typeof RadarIcon;
  color: string;
  streams: string[];
}) {
  return (
    <div
      style={{ "--agent-color": color } as React.CSSProperties}
      className="terminal-window flex min-h-[260px] flex-col rounded-xl border border-border/50 bg-card/60"
    >
      {/* Title bar */}
      <div className="flex items-center gap-3 border-b border-border/50 px-4 py-2.5">
        <div className="flex gap-1.5">
          <span
            className="status-dot"
            style={{ backgroundColor: `hsl(${color})` }}
          />
          <span className="status-dot bg-yellow-500/30" />
          <span className="status-dot bg-green-500/20" />
        </div>
        <p
          className="flex-1 font-mono text-[11px] font-semibold uppercase tracking-[0.2em]"
          style={{ color: `hsl(${color})` }}
        >
          {callsign}
        </p>
        <span className="shrink-0 rounded border border-border/40 bg-muted/20 px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest text-muted-foreground/60">
          STANDBY
        </span>
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-2 border-b border-border/30 bg-muted/20 px-4 py-2">
        <Icon className="size-3.5 shrink-0" style={{ color: `hsl(${color} / 0.7)` }} />
        <p className="flex-1 font-mono text-[10px] text-muted-foreground/60 truncate">{role}</p>
      </div>

      {/* Console body (completely static — zero state updates, zero re-renders) */}
      <div className="flex-1 p-4 space-y-2 overflow-hidden">
        <p className="font-mono text-[9px] uppercase tracking-[0.25em] text-muted-foreground/40 mb-3">
          CONSOLE //
        </p>
        <div className="space-y-2">
          {streams.map((line, i) => (
            <div
              key={`${i}-${line}`}
              className="flex items-center gap-2 font-mono text-[11px]"
            >
              <span style={{ color: `hsl(${color} / 0.6)` }}>▸</span>
              <span
                style={{
                  color:
                    i === streams.length - 1
                      ? `hsl(${color} / 0.85)`
                      : "hsl(var(--muted-foreground) / 0.5)",
                }}
              >
                {line}
              </span>
              {i === streams.length - 1 && (
                <span
                  className="terminal-cursor"
                  style={{ "--agent-color": `hsl(${color})` } as React.CSSProperties}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border/30 px-4 py-2">
        <p className="font-mono text-[9px] text-muted-foreground/40 tracking-widest">
          AWAITING MISSION DISPATCH
        </p>
      </div>
    </div>
  );
}

export function AgentEmptyState() {
  return (
    <div className="space-y-4">
      {/* Intro header */}
      <div className="text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-muted-foreground/50">
          TWO ANALYSTS · ONE KNOWLEDGE BUNDLE · INDEPENDENT INVESTIGATION
        </p>
      </div>

      {/* Agent terminals */}
      <div className="grid gap-4 md:grid-cols-2">
        <IdleTerminal
          callsign="AGENT://BRIEFING-01"
          role="Situation synthesis from retrieved evidence"
          Icon={RadarIcon}
          color="var(--agent-brief)"
          streams={BRIEFING_STREAMS}
        />
        <IdleTerminal
          callsign="AGENT://CRITIC-02"
          role="Assumption challenge · uncertainty mapping"
          Icon={ScaleIcon}
          color="var(--agent-analysis)"
          streams={CRITIC_STREAMS}
        />
      </div>

      <p className="text-center font-mono text-[10px] text-muted-foreground/40 tracking-widest">
        ▸ DISPATCH A QUERY TO ACTIVATE BOTH AGENTS
      </p>
    </div>
  );
}
