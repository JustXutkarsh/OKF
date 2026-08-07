"use client";

import { reportError } from "@/lib/monitoring";
import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

/**
 * Route-level error boundary (App Router). Catches anything thrown
 * above the local per-view boundaries so the app shows a professional
 * error UI instead of a blank page. Surfaces the request_id/digest
 * when available for correlation with backend logs.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    reportError(error, { component: "route", digest: error.digest });
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[60vh] max-w-lg flex-col items-center justify-center gap-4 px-4 text-center">
      <AlertTriangle className="size-8 text-destructive" />
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">Something went wrong</h1>
        <p className="text-sm text-muted-foreground">
          {error?.message || "An unexpected error occurred while rendering this page."}
        </p>
        {error?.digest && (
          <p className="text-xs text-muted-foreground/80">request_id: {error.digest}</p>
        )}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={reset}
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
        >
          Try again
        </button>
        <a
          href="/settings"
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
        >
          Check settings
        </a>
      </div>
    </main>
  );
}
