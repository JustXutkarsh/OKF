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
    refetchInterval: 30_000,
    retry: false,
  });
  const version = useQuery({
    queryKey: ["version"],
    queryFn: () => api.getVersion(),
    staleTime: 60_000,
    retry: false,
  });

  const apiOnline =
    ready.isSuccess && (ready.data.status === "ready" || ready.data.status === "ok");
  const bundleReady = ready.isSuccess && ready.data.checks.bundle_accessible;
  const consumerCount = ready.isSuccess
    ? Object.values(ready.data.checks.consumers).filter((c) => c.client_ready).length
    : 0;

  const indicators = [
    {
      id: "agents",
      label: `${consumerCount || 2} AGENTS ACTIVE`,
      live: consumerCount > 0 || ready.isPending,
      color: "hsl(var(--agent-brief))",
    },
    {
      id: "bundle",
      label: bundleReady
        ? `BUNDLE v${version.data?.bundle_version ?? "?"} READY`
        : ready.isPending
          ? "BUNDLE CHECKING"
          : "BUNDLE UNREADABLE",
      live: bundleReady || ready.isPending,
      color: bundleReady
        ? "hsl(var(--terminal-green))"
        : ready.isPending
          ? "hsl(var(--terminal-amber))"
          : "hsl(var(--terminal-red))",
    },
    {
      id: "api",
      label: ready.isPending ? "API CONNECTING" : apiOnline ? "API ONLINE" : "API OFFLINE",
      live: apiOnline || ready.isPending,
      color: apiOnline
        ? "hsl(var(--terminal-green))"
        : ready.isPending
          ? "hsl(var(--terminal-amber))"
          : "hsl(var(--terminal-red))",
    },
  ];

  return (
    <div className="flex items-center gap-3">
      {indicators.map((ind) => (
        <div key={ind.id} className="flex items-center gap-1.5">
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
