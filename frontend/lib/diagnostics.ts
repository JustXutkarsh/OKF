import type { ErrorContext } from "@/lib/monitoring";

// API diagnostics registry.
//
// Each successful request() records a small, SAFE snapshot of the
// response metadata (never API keys, never document contents —
// only identifiers and provenance fields). If rendering later fails,
// the error boundary pulls this snapshot so operators can correlate a
// blank/failed panel with the exact backend generation that fed it.

export interface RouteDiagnostics {
  /** Route path as passed to request(), e.g. "/analyze". */
  route: string;
  /** Wall time of the last request to this route, milliseconds. */
  durationMs?: number;
  provider?: string;
  model?: string;
  generatedAt?: string;
  bundleVersion?: number | string | null;
  /** Number of documents the backend reported using. */
  documentCount?: number;
  /** Correlation id, when the backend echoes one back. */
  requestId?: string;
}

// Fields that may appear on a successful payload and are safe to keep.
interface DiagnosticSource {
  provider?: string;
  model?: string;
  generated_at?: string;
  bundle_version?: number | string | null;
  documents_used?: string[];
  request_id?: string;
}

const registry = new Map<string, RouteDiagnostics>();

/** Update the snapshot for a route. Called from lib/api.ts after parse. */
export function recordDiagnostics(
  route: string,
  durationMs: number,
  payload?: unknown
): void {
  const source = (payload ?? {}) as DiagnosticSource;
  const next: RouteDiagnostics = {
    route,
    durationMs,
    provider: typeof source.provider === "string" ? source.provider : undefined,
    model: typeof source.model === "string" ? source.model : undefined,
    generatedAt: typeof source.generated_at === "string" ? source.generated_at : undefined,
    bundleVersion:
      typeof source.bundle_version === "number" || typeof source.bundle_version === "string"
        ? source.bundle_version
        : source.bundle_version === null
          ? null
          : undefined,
    documentCount: Array.isArray(source.documents_used)
      ? source.documents_used.length
      : undefined,
    requestId: typeof source.request_id === "string" ? source.request_id : undefined,
  };
  registry.set(route, { ...registry.get(route), ...next });
}

/** Snapshot recorded for a route, or undefined if it was never called. */
export function getDiagnostics(route: string): RouteDiagnostics | undefined {
  return registry.get(route);
}

/**
 * Build the ErrorContext for a render failure: route + provenance of the
 * data that was being rendered + request correlation id.
 */
export function diagnosticsContext(route: string, extra?: Partial<ErrorContext>): ErrorContext {
  const snap = getDiagnostics(route);
  return {
    route,
    requestId: snap?.requestId,
    ...extra,
  };
}

/** Human-readable provenance line for error UIs and console logs. */
export function describeDiagnostics(route: string): string {
  const snap = getDiagnostics(route);
  if (!snap) return `route ${route} (no request recorded)`;
  const parts = [
    `route ${route}`,
    snap.provider && `provider ${snap.provider}`,
    snap.model && `model ${snap.model}`,
    snap.generatedAt && `generated_at ${snap.generatedAt}`,
    snap.requestId && `request_id ${snap.requestId}`,
  ].filter(Boolean);
  return parts.join(", ");
}

/** Reset all snapshots (used by tests). */
export function clearDiagnostics(): void {
  registry.clear();
}
