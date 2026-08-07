"use client";

import { getDiagnostics } from "@/lib/diagnostics";
import type { UseQueryResult } from "@tanstack/react-query";

// Development-only query diagnostics. This whole module is dead-code
// eliminated from production bundles: every render site guards with
// `process.env.NODE_ENV === "development"` and the component itself
// hard-returns null otherwise.

export function DebugPanel({
  queryKey,
  query,
  route,
}: {
  /** The React Query cache key, stringified for display. */
  queryKey: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  query: UseQueryResult<any>;
  /** API route the query calls, so we can look up recorded metadata. */
  route: string;
}) {
  if (process.env.NODE_ENV !== "development") return null;

  const snap = getDiagnostics(route);
  const status = query.isPending ? "loading" : query.isError ? "error" : "success";

  return (
    <div
      data-testid="debug-panel"
      className="rounded-lg border border-dashed border-muted-foreground/40 bg-muted/30 p-3 font-mono text-xs text-muted-foreground"
    >
      <p className="mb-1 font-semibold uppercase tracking-wide">debug (dev only)</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        <dt>status</dt>
        <dd>{status}</dd>
        <dt>query_key</dt>
        <dd>{queryKey}</dd>
        <dt>last_request_ms</dt>
        <dd>{snap?.durationMs ?? "—"}</dd>
        <dt>document_count</dt>
        <dd>{snap?.documentCount ?? "—"}</dd>
        <dt>provider</dt>
        <dd>{snap?.provider ?? "—"}</dd>
        <dt>model</dt>
        <dd>{snap?.model ?? "—"}</dd>
        <dt>bundle_version</dt>
        <dd>{snap?.bundleVersion === null ? "null" : (snap?.bundleVersion ?? "—")}</dd>
      </dl>
    </div>
  );
}
