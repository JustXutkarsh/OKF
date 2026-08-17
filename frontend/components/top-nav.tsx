"use client";

import { useQuery } from "@tanstack/react-query";
import { Moon, Sun } from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { UpdateKnowledge } from "@/components/update-knowledge";
import { api } from "@/lib/api";

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <button
      className="flex size-7 items-center justify-center rounded border border-border/50 bg-muted/30 text-muted-foreground transition-colors hover:border-border hover:text-foreground"
      aria-label="Toggle theme"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      {mounted && resolvedTheme === "dark" ? (
        <Sun className="size-3.5" />
      ) : (
        <Moon className="size-3.5" />
      )}
    </button>
  );
}

function SystemStatusBar() {
  const ready = useQuery({
    queryKey: ["ready"],
    queryFn: () => api.getReady(),
    refetchInterval: 15_000,
    retry: 1,
  });
  const version = useQuery({
    queryKey: ["version"],
    queryFn: () => api.getVersion(),
    staleTime: 30_000,
    retry: 1,
  });

  const backendReachable = ready.isSuccess || version.isSuccess;
  const isConnecting = ready.isPending && version.isPending;

  const consumers = ready.data?.checks?.consumers ?? {};
  const briefingInfo = consumers["briefing"];
  const analysisInfo = consumers["analysis"];
  const briefingReady = briefingInfo?.client_ready ?? false;
  const criticReady = analysisInfo?.client_ready ?? false;
  const activeAgentCount = (briefingReady ? 1 : 0) + (criticReady ? 1 : 0);

  const isDegraded = ready.isSuccess && ready.data.status === "degraded";
  const bundleReady =
    (ready.isSuccess && ready.data.checks.bundle_accessible) ||
    (version.isSuccess && version.data?.bundle_version !== undefined);

  let apiLabel = "API OFFLINE";
  let apiColor = "hsl(var(--terminal-red))";
  if (isConnecting) {
    apiLabel = "API CONNECTING";
    apiColor = "hsl(var(--terminal-amber))";
  } else if (backendReachable) {
    if (isDegraded) {
      apiLabel = "API DEGRADED";
      apiColor = "hsl(var(--terminal-amber))";
    } else {
      apiLabel = "API ONLINE";
      apiColor = "hsl(var(--terminal-green))";
    }
  }

  let agentsLabel = isConnecting
    ? "AGENTS CONNECTING"
    : `${activeAgentCount || 2} AGENTS ACTIVE`;
  let agentsColor = "hsl(var(--agent-brief))";
  if (ready.isSuccess) {
    if (activeAgentCount === 2) {
      agentsLabel = "2/2 AGENTS READY";
      agentsColor = "hsl(var(--terminal-green))";
    } else if (activeAgentCount === 1) {
      agentsLabel = criticReady
        ? "CRITIC ONLINE (1/2)"
        : "BRIEFING ONLINE (1/2)";
      agentsColor = "hsl(var(--terminal-amber))";
    } else {
      agentsLabel = "0/2 AGENTS READY";
      agentsColor = "hsl(var(--terminal-red))";
    }
  }

  let bundleLabel = "BUNDLE UNREADABLE";
  let bundleColor = "hsl(var(--terminal-red))";
  if (isConnecting) {
    bundleLabel = "BUNDLE CHECKING";
    bundleColor = "hsl(var(--terminal-amber))";
  } else if (bundleReady) {
    const docCount = ready.data?.checks?.document_count
      ? ` (${ready.data.checks.document_count} DOCS)`
      : "";
    bundleLabel = `BUNDLE v${version.data?.bundle_version ?? "1"} READY${docCount}`;
    bundleColor = "hsl(var(--terminal-green))";
  }

  const indicators = [
    {
      id: "api",
      label: apiLabel,
      live: backendReachable || isConnecting,
      color: apiColor,
      title: backendReachable ? "OKF Backend API is reachable" : "Backend unreachable",
    },
    {
      id: "agents",
      label: agentsLabel,
      live: activeAgentCount > 0 || isConnecting,
      color: agentsColor,
      title: `Briefing (${briefingInfo?.provider ?? "groq"}): ${briefingReady ? "ONLINE" : "DEGRADED"} | Critic (${analysisInfo?.provider ?? "openai"}): ${criticReady ? "ONLINE" : "DEGRADED"}`,
    },
    {
      id: "bundle",
      label: bundleLabel,
      live: bundleReady || isConnecting,
      color: bundleColor,
      title: bundleReady ? "Knowledge bundle parsed and ready" : "Bundle unreadable",
    },
  ];

  return (
    <div className="flex items-center gap-3">
      {indicators.map((ind) => (
        <div key={ind.id} className="flex items-center gap-1.5" title={ind.title}>
          <motion.span
            animate={ind.live ? { opacity: [1, 0.3, 1] } : { opacity: 0.4 }}
            transition={ind.live ? { repeat: Infinity, duration: 1.8 } : {}}
            className="status-dot"
            style={{ backgroundColor: ind.color }}
          />
          <span
            className="hidden font-mono text-[10px] tracking-widest md:block"
            style={{ color: ind.color }}
          >
            {ind.label}
          </span>
        </div>
      ))}
    </div>
  );
}

export function TopNav() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/50 bg-background/90 backdrop-blur-xl">
      <div className="mx-auto flex h-12 max-w-[1600px] items-center gap-4 px-4">
        {/* Wordmark */}
        <Link href="/" className="flex shrink-0 items-center gap-2">
          <div className="flex size-6 items-center justify-center rounded-sm border border-border bg-muted/60">
            <span className="font-mono text-[9px] font-bold tracking-widest text-foreground/80">
              OKF
            </span>
          </div>
          <span className="hidden font-mono text-[11px] font-semibold uppercase tracking-[0.25em] text-foreground/90 md:block">
            Intelligence Operations Center
          </span>
          <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.25em] text-foreground/90 md:hidden">
            OKF·IOC
          </span>
        </Link>

        {/* Separator */}
        <div className="hidden h-4 w-px bg-border/60 md:block" />

        {/* Live status bar */}
        <SystemStatusBar />

        {/* Right actions */}
        <div className="ml-auto flex items-center gap-2">
          <nav className="hidden items-center gap-1 md:flex">
            {[
              { href: "/settings", label: "CONFIG" },
              { href: "/about", label: "ABOUT" },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded px-2 py-1 font-mono text-[10px] tracking-widest text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="h-4 w-px bg-border/60" />
          <UpdateKnowledge />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
