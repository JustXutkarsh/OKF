// Central reporting registry — Sentry-ready without the SDK.
//
// Errors from error boundaries, API diagnostics and manual captures are
// funnelled through `reportError`. Today there is a single built-in
// reporter (console). When Sentry is adopted, `lib/monitoring-init.ts`
// (or a plugin) can call `registerErrorReporter` with an adapter that
// forwards to `Sentry.captureException(error, { extra: context })`.
//
// Nothing here is allowed to receive API keys or document contents —
// reporters only see the safe ErrorContext shape.

export interface ErrorContext {
  /** Which API route produced the data being rendered, e.g. "/analyze". */
  route?: string;
  /** UI component that failed, e.g. "AnalysisView". */
  component?: string;
  /** Backend correlation id, when the backend provided one. */
  requestId?: string;
  /** Digest Next.js attaches to production route errors. */
  digest?: string;
}

export type ErrorReporter = (error: unknown, context: ErrorContext) => void;

const reporters = new Set<ErrorReporter>();

/**
 * Plug in an error reporting backend. Returns an unsubscribe function.
 * Example (future):
 *   registerErrorReporter((error, ctx) => Sentry.captureException(error, { extra: ctx }));
 */
export function registerErrorReporter(reporter: ErrorReporter): () => void {
  reporters.add(reporter);
  return () => reporters.delete(reporter);
}

/** Report an error to every registered sink. Never throws. */
export function reportError(error: unknown, context: ErrorContext = {}): void {
  if (reporters.size === 0) {
    // Fallback sink: keep diagnostics visible in the browser console.
    console.error("[okf:report]", context, error);
    return;
  }
  for (const reporter of reporters) {
    try {
      reporter(error, context);
    } catch {
      // A broken reporter must never break the app.
    }
  }
}
